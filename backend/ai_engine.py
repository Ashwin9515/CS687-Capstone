from datetime import date
from models import plan_item, plan_doc, recommendation_doc
from statistics import mean

def generate_plan(user, behavior_model, db):
    user_id = user["userId"]

    # Safe intensity fallback
    try:
        intensity = behavior_model.next_best_intensity(user_id) or "Moderate"
    except Exception:
        intensity = "Moderate"

    # Rule-based plans (LLM-ready)
    base = {
        "Low": [
            plan_item("Workout", "Low", 20, "Light mobility + walk"),
            plan_item("Habit", "Low", 5, "Hydrate: +1L"),
            plan_item("Recovery", "Low", 10, "Stretch + sleep target 8h"),
        ],
        "Moderate": [
            plan_item("Workout", "Moderate", 35, "Bodyweight circuit + brisk walk"),
            plan_item("Habit", "Low", 5, "2L water + protein target"),
            plan_item("Recovery", "Low", 10, "Cooldown + mindfulness 5m"),
        ],
        "High": [
            plan_item("Workout", "High", 45, "Intervals + strength"),
            plan_item("Habit", "Low", 5, "Macros check + 2.5L water"),
            plan_item("Recovery", "Low", 15, "Mobility + sleep hygiene"),
        ],
    }

    items = base.get(intensity, base["Moderate"])

    # Consistent schema (rename plan_date → date in models.py)
    plan = plan_doc(
        user_id=user_id,
        items=items,
        date=date.today().isoformat(),
        status="Proposed"
    )

    # Upsert today's plan
    db.plans.update_one(
        {"userId": user_id, "date": plan["date"]},
        {"$set": plan},
        upsert=True
    )
    return plan


def generate_nudges(user_id, behavior_model, db):
    # Fetch last 6 step entries
    cursor = db.sensordata.find(
        {"userId": user_id, "metricType": "Steps"}
    ).sort("ts", -1).limit(6)

    recent_steps = [int(m["value"]) for m in cursor if "value" in m]
    avg = int(mean(recent_steps)) if recent_steps else 0

    if avg < 300:
        msg = "Quick win: 10-minute brisk walk to boost your step count."
    elif avg < 2000:
        msg = "Great start! Add another short walk to hit your daily goal."
    else:
        msg = "Nice pace! Add a 5-minute stretch break to stay loose."

    rec = recommendation_doc(user_id, msg, context="nudge")
    db.recommendations.insert_one(rec)
    return rec
