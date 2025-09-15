from datetime import date
from models import plan_item, plan_doc, recommendation_doc

def generate_plan(user, behavior_model, db):
    user_id = user["userId"]
    intensity = behavior_model.next_best_intensity(user_id)

    # Simple rules → you can swap this with an LLM later.
    base = {
        "Low":    [plan_item("Workout","Low",20,"Light mobility + walk"),
                   plan_item("Habit","Low",5,"Hydrate: +1L"),
                   plan_item("Recovery","Low",10,"Stretch + sleep target 8h")],
        "Moderate":[plan_item("Workout","Moderate",35,"Bodyweight circuit + brisk walk"),
                   plan_item("Habit","Low",5,"2L water + protein target"),
                   plan_item("Recovery","Low",10,"Cooldown + mindfulness 5m")],
        "High":   [plan_item("Workout","High",45,"Intervals + strength"),
                   plan_item("Habit","Low",5,"Macros check + 2.5L water"),
                   plan_item("Recovery","Low",15,"Mobility + sleep hygiene")]
    }

    items = base[intensity]
    plan = plan_doc(user_id=user_id, items=items, plan_date=date.today().isoformat(), status="Proposed")

    # Upsert today's plan
    db.plans.update_one({"userId": user_id, "date": plan["date"]}, {"$set": plan}, upsert=True)
    return plan

def generate_nudges(user_id, behavior_model, db):
    # Example: step-count & inactivity nudge
    from statistics import mean
    recent_steps = [m["value"] for m in db.sensordata.find({"userId": user_id, "metricType":"Steps"}).sort("ts", -1).limit(6)]
    avg = int(mean(recent_steps)) if recent_steps else 0
    if avg < 300:  # very low recent steps
        msg = "Quick win: 10-minute brisk walk to boost your step count."
    else:
        msg = "Nice pace! Add a 5-minute stretch break to stay loose."
    rec = recommendation_doc(user_id, msg, context="nudge")
    db.recommendations.insert_one(rec)
    return rec
