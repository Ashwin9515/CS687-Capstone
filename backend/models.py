from __future__ import annotations
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union

# Type alias for numeric values
Number = Union[int, float]

# ---- helpers ----

def iso_today() -> str:
    return date.today().isoformat()

def _coerce_metric_value(metric_type: str, value: Any) -> Number:
    """
    Best-effort numeric coercion so analytics don't break on strings.
    Steps → int, HR/SleepScore → float, else try float.
    """
    try:
        if metric_type == "Steps":
            return int(value)
        if metric_type in {"HR", "SleepScore"}:
            return float(value)
        return float(value)
    except (TypeError, ValueError):
        return value  # Last resort fallback — caller must guard

# ---- document factories ----

def user_doc(user_id: str = "U123", name: str = "Demo User") -> Dict[str, Any]:
    return {
        "userId": user_id,
        "name": name,
        "preferences": {
            "daysPerWeek": 4,
            "equip": ["bodyweight", "dumbbells"]
        },
        "createdAt": datetime.utcnow(),
    }

def sensordata_doc(
    user_id: str,
    metric_type: str,
    value: Any,
    ts: Optional[datetime] = None,
    device_id: str = "DEV1",
    date_str: Optional[str] = None,
) -> Dict[str, Any]:
    doc = {
        "userId": user_id,
        "deviceId": device_id,
        "ts": ts or datetime.utcnow(),
        "metricType": metric_type,
        "value": _coerce_metric_value(metric_type, value),
    }
    if date_str:
        doc["date"] = date_str  # Optional: pre-processed day-level key
    return doc

def plan_doc(
    user_id: str,
    items: List[Dict[str, Any]],
    date: Optional[str] = None,
    status: str = "Proposed",
) -> Dict[str, Any]:
    return {
        "userId": user_id,
        "date": date or iso_today(),
        "items": items,
        "status": status,
    }

def plan_item(
    _type: str,
    intensity: str,
    duration_min: Number,
    notes: str = "",
) -> Dict[str, Any]:
    return {
        "type": _type,
        "intensity": intensity,
        "durationMin": duration_min,
        "notes": notes,
    }

def feedback_doc(
    user_id: str,
    rpe: Optional[Number] = None,
    mood: Optional[str] = None,
    pain: str = "none",
    notes: str = "",
    ts: Optional[datetime] = None,
) -> Dict[str, Any]:
    return {
        "userId": user_id,
        "rpe": rpe,
        "mood": mood,
        "pain": pain,
        "notes": notes,
        "ts": ts or datetime.utcnow(),
    }

def recommendation_doc(
    user_id: str,
    message: str,
    context: str = "",
    ts: Optional[datetime] = None,
) -> Dict[str, Any]:
    return {
        "userId": user_id,
        "message": message,
        "context": context,
        "ts": ts or datetime.utcnow(),
    }
