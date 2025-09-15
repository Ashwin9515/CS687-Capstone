from datetime import datetime, date

def user_doc(user_id="U123", name="Demo User"):
    return {"userId": user_id, "name": name, "goals": [{"metric":"fatLoss","target":-2.0,"due":"2025-12-31"}], "preferences":{"daysPerWeek":4,"equip":["bodyweight","dumbbells"]}}

def sensordata_doc(user_id, metric_type, value, ts=None, device_id="DEV1"):
    return {"userId": user_id, "deviceId": device_id, "ts": ts or datetime.utcnow(), "metricType": metric_type, "value": value}

def plan_doc(user_id, items, plan_date=None, status="Proposed"):
    return {"userId": user_id, "date": (plan_date or date.today().isoformat()),
            "items": items, "status": status}

def plan_item(_type, intensity, duration_min, notes=""):
    return {"type": _type, "intensity": intensity, "durationMin": duration_min, "notes": notes}

def feedback_doc(user_id, rpe=None, mood=None, pain="none", notes="", ts=None):
    return {"userId": user_id, "rpe": rpe, "mood": mood, "pain": pain, "notes": notes, "ts": ts or datetime.utcnow()}

def recommendation_doc(user_id, message, context="", ts=None):
    return {"userId": user_id, "message": message, "context": context, "ts": ts or datetime.utcnow()}
