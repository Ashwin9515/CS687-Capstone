from datetime import datetime, timedelta, date
from statistics import mean

# Configurable defaults
DEFAULT_HR_BASELINE = 75.0
DEFAULT_SLEEP_SCORE_BASELINE = 70.0

def _clamp(x, lo=0.1, hi=1.0):
    return max(lo, min(hi, x))

class BehaviorModel:
    """
    Lightweight behavior model to adapt workout intensity:
    - adherence_score(): based on past plan completion rate
    - readiness_score(): normalized physiological indicators (HR, SleepScore)
    - next_best_intensity(): suggested level with hysteresis for stability
    """
    
    def __init__(self, db):
        self.db = db

    def _recent_plans(self, user_id, days=7):
        since_str = (date.today() - timedelta(days=days)).isoformat()
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

    def adherence_score(self, user_id, days=7):
        plans = self._recent_plans(user_id, days)
        if not plans:
            return 0.5  # neutral fallback
        completed = sum(1 for p in plans if p.get("status") == "Completed")
        return completed / len(plans)

    def readiness_score(self, user_id):
        # Baseline data from past 14 days
        hr_base_vals = self._values(user_id, "HR", hours=24 * 14)
        sleep_base_vals = self._values(user_id, "SleepScore", hours=24 * 14)

        hr_baseline = mean(hr_base_vals) if hr_base_vals else DEFAULT_HR_BASELINE
        sleep_baseline = mean(sleep_base_vals) if sleep_base_vals else DEFAULT_SLEEP_SCORE_BASELINE

        # Recent HR and SleepScore
        hr_recent = self._values(user_id, "HR", hours=24)
        sleep_recent = self._values(user_id, "SleepScore", hours=24 * 7)[:3]  # take latest 3 scores

        hr_avg = mean(hr_recent) if hr_recent else hr_baseline
        sleep_avg = mean(sleep_recent) if sleep_recent else sleep_baseline

        # Normalize: HR ↓ is better, SleepScore ↑ is better
        hr_delta = hr_baseline - hr_avg
        hr_score = _clamp(0.5 + (hr_delta / 20.0))  # normalize ±20 bpm to [0,1]
        sleep_score = _clamp(sleep_avg / 100.0)

        readiness = round(0.4 * hr_score + 0.6 * sleep_score, 2)
        return readiness

    def next_best_intensity(self, user_id):
        readiness = self.readiness_score(user_id)
        adherence = self.adherence_score(user_id)

        # Initial suggestion
        if readiness > 0.8 and adherence >= 0.6:
            target = "High"
        elif readiness >= 0.6:
            target = "Moderate"
        else:
            target = "Low"

        # Hysteresis to prevent large jumps
        last_plan = self.db.plans.find_one(
            {"userId": user_id},
            sort=[("date", -1)],
            projection={"_id": 0, "items": 1}
        )

        last_intensity = None
        if last_plan and last_plan.get("items"):
            for item in last_plan["items"]:
                if item.get("type") == "Workout":
                    last_intensity = item.get("intensity")
                    break

        if last_intensity:
            order = {"Low": 0, "Moderate": 1, "High": 2}
            li = order.get(last_intensity, 1)
            ti = order.get(target, 1)
            if abs(ti - li) > 1:
                target = "Moderate"

        return target
