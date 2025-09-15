from datetime import datetime, timedelta
from statistics import mean

class MCPBehaviorModel:
    """
    Tiny behavior model:
    - adherenceScore: completion ratio of last 7 days
    - readinessScore: simple readiness from HR delta + sleepScore proxy
    """

    def __init__(self, db):
        self.db = db

    def _recent_plans(self, user_id, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        return list(self.db.plans.find({"userId": user_id, "date": {"$gte": since}}))

    def _recent_metrics(self, user_id, hours=24):
        since = datetime.utcnow() - timedelta(hours=hours)
        cur = list(self.db.sensordata.find({"userId": user_id, "ts": {"$gte": since}}))
        return cur

    def adherence_score(self, user_id):
        plans = self._recent_plans(user_id)
        if not plans:
            return 0.5
        completed = sum(1 for p in plans if p.get("status") == "Completed")
        return round(completed / len(plans), 2)

    def readiness_score(self, user_id):
        metrics = self._recent_metrics(user_id, hours=24)
        if not metrics:
            return 0.6
        hr = [m["value"] for m in metrics if m["metricType"] == "HR"]
        sleep = [m["value"] for m in metrics if m["metricType"] == "SleepScore"]
        hr_avg = mean(hr) if hr else 75
        sleep_avg = mean(sleep) if sleep else 70
        # Normalize: lower HR better, higher sleep better
        readiness = (0.5 * (80 / max(hr_avg, 40)) + 0.5 * (sleep_avg / 100))
        return max(0.1, min(1.0, round(readiness, 2)))

    def next_best_intensity(self, user_id):
        r = self.readiness_score(user_id)
        a = self.adherence_score(user_id)
        if r > 0.8 and a >= 0.6:
            return "High"
        if r >= 0.6:
            return "Moderate"
        return "Low"
