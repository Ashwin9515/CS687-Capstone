from datetime import datetime, timedelta, date
from statistics import mean

def _clamp(x, lo=0.1, hi=1.0):
    return max(lo, min(hi, x))

class BehaviorModel:
    """
    Tiny behavior model (robust version):
    - adherenceScore: completion ratio of last N days
    - readinessScore: normalized vs 14-day baselines (HR ↓ better, SleepScore ↑ better)
    - next_best_intensity: thresholds + mild hysteresis to avoid flip-flop
    """

    def __init__(self, db):
        self.db = db

    # helpers
    def _recent_plans(self, user_id, days=7):
        since_str = (date.today() - timedelta(days=days)).isoformat()
        # Only fetch what we need
        cur = self.db.plans.find(
            {"userId": user_id, "date": {"$gte": since_str}},
            {"_id": 0, "status": 1, "date": 1}
        )
        return list(cur)

    def _values(self, user_id, metric, hours=24, limit=500):
        """Fetch numeric metric values in a window; ignore non-numeric."""
        since = datetime.utcnow() - timedelta(hours=hours)
        cur = self.db.sensordata.find(
            {"userId": user_id, "metricType": metric, "ts": {"$gte": since}},
            {"_id": 0, "value": 1, "ts": 1}
        ).sort("ts", -1).limit(limit)
        vals = []
        for d in cur:
            try:
                vals.append(float(d["value"]))
            except (ValueError, TypeError, KeyError):
                continue
        return vals

    # scores
    def adherence_score(self, user_id, days=7):
        plans = self._recent_plans(user_id, days)
        if not plans:
            return 0.5
        completed = sum(1 for p in plans if p.get("status") == "Completed")
        return round(completed / len(plans), 2)

    def readiness_score(self, user_id):
        # Baselines from last 14 days
        hr_base_vals = self._values(user_id, "HR", hours=24*14)
        sleep_base_vals = self._values(user_id, "SleepScore", hours=24*14)
        hr_baseline = mean(hr_base_vals) if hr_base_vals else 75.0
        sleep_baseline = mean(sleep_base_vals) if sleep_base_vals else 70.0

        # Recent window (HR last 24h; last ~3 sleep scores in the past week)
        hr_recent = self._values(user_id, "HR", hours=24)
        sleep_recent = self._values(user_id, "SleepScore", hours=24*7)[:3]

        hr_avg = mean(hr_recent) if hr_recent else hr_baseline
        sleep_avg = mean(sleep_recent) if sleep_recent else sleep_baseline

        # Normalize to 0–1: lower HR vs baseline is better; higher sleep is better
        hr_delta = hr_baseline - hr_avg            # positive is good
        hr_score = _clamp(0.5 + (hr_delta / 20.0)) # ~±20 bpm spans 0–1
        sleep_score = _clamp(sleep_avg / 100.0)

        readiness = round(0.4 * hr_score + 0.6 * sleep_score, 2)
        return readiness

    # policy
    def next_best_intensity(self, user_id):
        r = self.readiness_score(user_id)
        a = self.adherence_score(user_id)

        # Base thresholds
        if r > 0.8 and a >= 0.6:
            target = "High"
        elif r >= 0.6:
            target = "Moderate"
        else:
            target = "Low"

        # Mild hysteresis: step only one level at a time vs last plan
        last = self.db.plans.find_one(
            {"userId": user_id},
            sort=[("date", -1)],
            projection={"_id": 0, "items": 1}
        )
        last_intensity = None
        if last and last.get("items"):
            for it in last["items"]:
                if it.get("type") == "Workout":
                    last_intensity = it.get("intensity")
                    break

        if last_intensity:
            order = {"Low": 0, "Moderate": 1, "High": 2}
            li = order.get(last_intensity, 1)
            ti = order.get(target, 1)
            if ti - li > 1:   # jumping Low -> High
                target = "Moderate"
            elif li - ti > 1: # jumping High -> Low
                target = "Moderate"

        return target