import os
import uuid
import time
import json
import logging
from datetime import date, datetime, timedelta
from bson import ObjectId

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from dotenv import load_dotenv

# Optional TLS CA bundle for MongoDB Atlas
try:
    import certifi  # type: ignore
    _CERT_PATH = certifi.where()
except Exception:
    _CERT_PATH = None

# Auth (JWT optional; we still support X-User-Id)
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt_identity, jwt_required
)

# --- project modules ---
from models import user_doc, sensordata_doc, feedback_doc
from rules import BehaviorModel
from system_function import generate_plan, generate_nudges

# ----------------- logging -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- setup -----------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "ai_fitness")

def make_client(uri: str) -> MongoClient:
    """Create a Mongo client with TLS for Atlas."""
    kwargs = {"serverSelectionTimeoutMS": 30000}
    if uri.startswith("mongodb+srv://") or "mongodb.net" in uri:
        kwargs["tls"] = True
        if _CERT_PATH:
            kwargs["tlsCAFile"] = _CERT_PATH
    return MongoClient(uri, **kwargs)

app = Flask(__name__)
CORS(app)

# JWT (optional)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
app.config["JWT_TOKEN_LOCATION"] = ["headers"]  # Authorization: Bearer <token>
jwt = JWTManager(app)

client = make_client(MONGO_URI)
db = client[DB_NAME]

behavior = BehaviorModel(db)

# ----------------- helpers -----------------
def get_user_id() -> str:
    """Prefer JWT identity; else X-User-Id; else stable dev fallback."""
    identity = get_jwt_identity()
    if identity:
        return identity
    user_id = request.headers.get("X-User-Id")
    if not user_id:
        user_id = "U123"  # stable fallback for dev/demo
        logger.warning("No auth provided; using fallback userId U123")
    return user_id

def _normalize_plan_doc(doc):
    """Return a JSON-safe plan dict."""
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    for k in ("date", "ts", "startedAt"):
        if isinstance(d.get(k), (datetime, date)):
            d[k] = d[k].isoformat()
    return d

def video_doc(user_id: str, title: str, url: str, tags=None):
    return {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "title": title,
        "url": url,
        "tags": tags or [],
        "ts": datetime.now(datetime.UTC),
    }

def ensure_indexes():
    try:
        db.sensordata.create_index([("userId", 1), ("metricType", 1), ("ts", -1)])
        db.plans.create_index([("userId", 1), ("date", 1)])
        db.goals.create_index([("userId", 1), ("createdAt", -1)])
        db.recommendations.create_index([("userId", 1), ("ts", -1)])
        db.videos.create_index([("id", 1)], unique=True)
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")

# ----------------- seed workout videos -----------------
def seed_videos_if_empty():
    if db.videos.count_documents({}) > 0:
        return
    seed = [
        {"id": "vid-hand", "userId": "system", "title": "Hand Workout",
         "url": "https://youtu.be/dCtwWNTnOq4?si=SdnfaFW4FoTPY0mQ", "tags": ["hand","arms"], "ts": datetime.now(datetime.UTC)},
        {"id": "vid-leg", "userId": "system", "title": "Leg Workout",
         "url": "https://youtu.be/ZZI__bqlBkQ?si=-EKIMAmKT1irFzQB", "tags": ["legs","lowerbody"], "ts": datetime.now(datetime.UTC)},
        {"id": "vid-chest", "userId": "system", "title": "Chest Workout",
         "url": "https://youtu.be/Qv4AvwQq5ok?si=GhPuNYhpGu2gM5S2", "tags": ["chest","upperbody"], "ts": datetime.now(datetime.UTC)},
        {"id": "vid-shoulder", "userId": "system", "title": "Shoulder Workout",
         "url": "https://youtu.be/mUI4hXTmAkw?si=T1WzHASxkyjzFOi7", "tags": ["shoulder","upperbody"], "ts": datetime.now(datetime.UTC)},
        {"id": "vid-mobility-10", "userId": "system", "title": "10-Minute Morning Mobility",
         "url": "https://www.youtube.com/watch?v=Z4ziWoIo6lM", "tags": ["mobility","stretch"], "ts": datetime.now(datetime.UTC)},
        {"id": "vid-hiit-20", "userId": "system", "title": "20-Minute Full Body HIIT",
         "url": "https://www.youtube.com/watch?v=ml6cT4AZdqI", "tags": ["hiit","cardio"], "ts": datetime.now(datetime.UTC)},
    ]
    db.videos.insert_many(seed)

try:
    ensure_indexes()
    seed_videos_if_empty()
except Exception as se:
    logger.warning(f"[Startup] Issue: {se}")

# ----------------- error handling -----------------
@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception")
    return jsonify({"success": False, "error": str(e)}), 500

# ----------------- routes -----------------
@app.get("/")
def root():
    return {
        "service": "ai-fitness-backend",
        "ok": True,
        "endpoints": [
            "/health", "/auth/login", "/me",
            "/me/metrics", "/me/metrics/steps",
            "/me/plan", "/me/plan/start", "/me/plan/complete",
            "/me/plan/week", "/me/plan/week/regenerate",
            "/me/plan/<YYYY-MM-DD>/start", "/me/plan/<YYYY-MM-DD>/complete",
            "/me/recommendations", "/me/nudge", "/me/feedback",
            "/coach/ask", "/stream/nudges",
            "/videos (GET/POST)", "/videos/delete (POST)",
            "/me/goals (GET/POST)", "/me/goals/<id> (PATCH/DELETE)",
        ]
    }

@app.get("/health")
def health():
    status = "ok"
    try:
        client.admin.command("ping")
    except Exception:
        status = "degraded"
    return {"status": status, "time": datetime.now(datetime.UTC).isoformat()}

# --- auth / user ---
@app.post("/auth/login")
def login():
    """
    Accepts: { userId: string, name?: string }
    Returns: { userId, name, access_token }
    """
    body = request.json or {}
    user_id = body.get("userId", "U123")
    name = body.get("name", "Demo User")
    try:
        if not db.users.find_one({"userId": user_id}):
            db.users.insert_one(user_doc(user_id, name))
        token = create_access_token(identity=user_id)
        return {"userId": user_id, "name": name, "access_token": token}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.get("/me")
@jwt_required(optional=True)
def me():
    user_id = get_user_id()
    try:
        user = db.users.find_one({"userId": user_id}) or user_doc(user_id)
        return {"userId": user_id, "name": user.get("name", "Demo User")}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- metrics ---
@app.post("/me/metrics")
@jwt_required(optional=True)
def ingest_metrics():
    """Insert metrics samples (HR, Steps, SleepScore, etc.)."""
    user_id = get_user_id()
    payload = request.json
    if payload is None:
        return jsonify({"error": "invalid_json"}), 400

    items = payload if isinstance(payload, list) else [payload]
    docs = []
    for m in items:
        mt = (m or {}).get("metricType")
        val = (m or {}).get("value")
        if mt is None or val is None:
            return jsonify({"error": "missing_fields", "detail": "metricType and value required"}), 400
        docs.append(sensordata_doc(user_id, mt, val))

    try:
        if docs:
            db.sensordata.insert_many(docs)
        return {"ingested": len(docs)}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/metrics/steps")
@jwt_required(optional=True)
def set_steps():
    """Overwrite today's step count for the current user (one record per day)."""
    user_id = get_user_id()
    body = request.json or {}
    steps = int(body.get("value", 0))
    today = date.today().isoformat()

    # use models.sensordata_doc day-level rollup
    doc = sensordata_doc(user_id, "Steps", steps, date_str=today)

    try:
        db.sensordata.update_one(
            {"userId": user_id, "metricType": "Steps", "date": today},
            {"$set": doc},
            upsert=True
        )
        return {"ok": True, "steps": steps, "date": today}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.get("/me/metrics")
@jwt_required(optional=True)
def list_metrics():
    user_id = get_user_id()
    try:
        cur = db.sensordata.find({"userId": user_id}).sort("ts", -1).limit(50)
        return jsonify([
            {"metricType": d["metricType"], "value": d["value"], "ts": d["ts"].isoformat()}
            for d in cur
        ])
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- daily plan ---
@app.get("/me/plan")
@jwt_required(optional=True)
def get_plan():
    user_id = get_user_id()
    today = date.today().isoformat()
    try:
        raw = db.plans.find_one({"userId": user_id, "date": today}, {"_id": 0})
        if not raw:
            user = db.users.find_one({"userId": user_id}) or user_doc(user_id)
            raw = generate_plan(user, behavior, db)
        return jsonify(_normalize_plan_doc(raw))
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/plan/start")
@jwt_required(optional=True)
def start_plan():
    user_id = get_user_id()
    today = date.today().isoformat()
    try:
        db.plans.update_one(
            {"userId": user_id, "date": today},
            {"$set": {"status": "In Progress", "startedAt": datetime.now(datetime.UTC)}},
            upsert=True
        )
        doc = db.plans.find_one({"userId": user_id, "date": today}, {"_id": 0})
        return jsonify(_normalize_plan_doc(doc))
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/plan/complete")
@jwt_required(optional=True)
def complete_plan():
    user_id = get_user_id()
    today = date.today().isoformat()
    try:
        db.plans.update_one(
            {"userId": user_id, "date": today},
            {"$set": {"status": "Completed"}},
            upsert=True
        )
        return {"status": "Completed"}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- week planning ---
def _upsert_plan_for_date(user_id: str, the_date: date):
    user = db.users.find_one({"userId": user_id}) or user_doc(user_id)
    plan = generate_plan(user, behavior, db)  # dict
    d = dict(plan)
    d["userId"] = user_id
    d["date"] = the_date.isoformat()
    d.pop("_id", None)
    db.plans.update_one(
        {"userId": user_id, "date": d["date"]},
        {"$set": d},
        upsert=True
    )
    return d

@app.get("/me/plan/week")
@jwt_required(optional=True)
def get_week_plan():
    """Return plans for today + next 6 days; generate missing ones."""
    user_id = get_user_id()
    today = date.today()
    out = []
    try:
        for i in range(7):
            dy = today + timedelta(days=i)
            existing = db.plans.find_one({"userId": user_id, "date": dy.isoformat()}, {"_id": 0})
            if not existing:
                existing = _upsert_plan_for_date(user_id, dy)
            out.append(_normalize_plan_doc(existing))
        return jsonify(out)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/plan/week/regenerate")
@jwt_required(optional=True)
def regenerate_week_plan():
    user_id = get_user_id()
    today = date.today()
    out = []
    try:
        for i in range(7):
            dy = today + timedelta(days=i)
            out.append(_normalize_plan_doc(_upsert_plan_for_date(user_id, dy)))
        return jsonify({"ok": True, "plans": out})
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/plan/<the_date>/start")
@jwt_required(optional=True)
def start_plan_on_date(the_date):
    user_id = get_user_id()
    try:
        y, m, d = map(int, the_date.split("-"))
        _upsert_plan_for_date(user_id, date(y, m, d))
        db.plans.update_one(
            {"userId": user_id, "date": the_date},
            {"$set": {"status": "In Progress", "startedAt": datetime.now(datetime.UTC)}},
            upsert=True
        )
        doc = db.plans.find_one({"userId": user_id, "date": the_date}, {"_id": 0})
        return jsonify(_normalize_plan_doc(doc))
    except (ValueError, PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "bad_date_or_db", "detail": str(e)}), 400

@app.post("/me/plan/<the_date>/complete")
@jwt_required(optional=True)
def complete_plan_on_date(the_date):
    user_id = get_user_id()
    try:
        db.plans.update_one(
            {"userId": user_id, "date": the_date},
            {"$set": {"status": "Completed"}},
            upsert=True
        )
        doc = db.plans.find_one({"userId": user_id, "date": the_date}, {"_id": 0})
        return jsonify(_normalize_plan_doc(doc))
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- recommendations / nudges ---
@app.get("/me/recommendations")
@jwt_required(optional=True)
def get_recs():
    user_id = get_user_id()
    try:
        cur = db.recommendations.find({"userId": user_id}).sort("ts", -1).limit(20)
        return jsonify([
            {"message": r["message"], "ts": r["ts"].isoformat(), "context": r.get("context", "")}
            for r in cur
        ])
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/nudge")
@jwt_required(optional=True)
def make_nudge():
    user_id = get_user_id()
    try:
        rec = generate_nudges(user_id, behavior, db)
        return {"message": rec["message"], "ts": rec["ts"].isoformat()}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- feedback ---
@app.post("/me/feedback")
@jwt_required(optional=True)
def give_feedback():
    user_id = get_user_id()
    body = request.json or {}
    try:
        doc = feedback_doc(
            user_id,
            rpe=body.get("rpe"),
            mood=body.get("mood"),
            pain=body.get("pain", "none"),
            notes=body.get("notes", "")
        )
        db.feedback.insert_one(doc)
        return {"ok": True}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- AI Coach ---
@app.post("/coach/ask")
@jwt_required(optional=True)
def coach_ask():
    """
    JSON in:  { "message": "I'm sore today..." }
    JSON out: { "reply": "..." }
    """
    body = request.get_json(silent=True) or {}
    msg = (body.get("message") or "").strip()
    user_id = get_user_id()
    if not msg:
        return jsonify({"reply": "Tell me how you’re feeling or what you want to work on today."})
    reply = (
        f"I hear you, {user_id}. From what you shared — “{msg}” — "
        "try a light 20-minute walk, 5 minutes of breathing, and gentle mobility. "
        "Hydrate and aim for 7–9 hours of sleep tonight."
    )
    return jsonify({"reply": reply})

# --- Workout Videos CRUD ---
@app.get("/videos")
@jwt_required(optional=True)
def list_videos():
    """List workout videos (latest first)."""
    try:
        cur = db.videos.find().sort("ts", -1).limit(200)
        out = []
        for v in cur:
            out.append({
                "id": v.get("id"),
                "title": v.get("title"),
                "url": v.get("url"),
                "tags": v.get("tags", []),
                "ts": v["ts"].isoformat() if isinstance(v.get("ts"), datetime) else v.get("ts"),
            })
        return jsonify(out)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/videos")
@jwt_required(optional=True)
def add_or_update_video():
    """
    Create or update a video.
    Body: { title, url, tags?: [..], id?: "existing-id" }
    If id provided and found -> update (owner-only); else create new.
    """
    user_id = get_user_id()
    body = request.json or {}
    title = (body.get("title") or "").strip()
    url   = (body.get("url") or "").strip()
    tags  = body.get("tags") or []
    vid_id = body.get("id")

    if not title or not url:
        return jsonify({"error": "missing_fields", "detail": "title and url required"}), 400

    try:
        if vid_id:
            existing = db.videos.find_one({"id": vid_id})
            if existing:
                # only owner can update; protect system videos
                if existing.get("userId") == "system":
                    return jsonify({"error": "forbidden", "detail": "system videos cannot be modified"}), 403
                if existing.get("userId") != user_id:
                    return jsonify({"error": "forbidden"}), 403
                db.videos.update_one({"id": vid_id}, {"$set": {
                    "title": title, "url": url, "tags": tags, "ts": datetime.now(datetime.UTC)
                }})
                doc = db.videos.find_one({"id": vid_id}, {"_id": 0})
            else:
                newdoc = video_doc(user_id, title, url, tags)
                newdoc["id"] = vid_id
                db.videos.insert_one(newdoc)
                doc = {k: v for k, v in newdoc.items() if k != "_id"}
        else:
            newdoc = video_doc(user_id, title, url, tags)
            db.videos.insert_one(newdoc)
            doc = {k: v for k, v in newdoc.items() if k != "_id"}

        if isinstance(doc.get("ts"), datetime):
            doc["ts"] = doc["ts"].isoformat()
        return jsonify(doc)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/videos/delete")
@jwt_required(optional=True)
def delete_video():
    """Delete a video by id. Body: { id }"""
    body = request.json or {}
    vid_id = body.get("id")
    if not vid_id:
        return jsonify({"error": "missing_id"}), 400
    try:
        v = db.videos.find_one({"id": vid_id})
        if not v:
            return jsonify({"error": "not_found"}), 404
        if v.get("userId") == "system":
            return jsonify({"error": "forbidden", "detail": "system videos cannot be deleted"}), 403
        if v.get("userId") != get_user_id():
            return jsonify({"error": "forbidden"}), 403
        db.videos.delete_one({"id": vid_id})
        return {"ok": True}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

# --- GOALS (CRUD + live progress) ---
def _steps_today(user_id):
    today = date.today().isoformat()
    total = 0
    for d in db.sensordata.find({"userId": user_id, "metricType": "Steps", "date": today}):
        total += int(d.get("value", 0))
    if total == 0:
        # fallback: sum today via ts field (older entries may not have 'date')
        for d in db.sensordata.find({"userId": user_id, "metricType": "Steps"}):
            ts = d.get("ts")
            if isinstance(ts, datetime) and ts.date().isoformat() == today:
                total += int(d.get("value", 0))
    return total

def _active_minutes_today_from_plan(user_id):
    today = date.today().isoformat()
    p = db.plans.find_one({"userId": user_id, "date": today}) or {}
    mins = 0
    for it in (p.get("items") or []):
        if it.get("type") == "Workout":
            mins += int(it.get("durationMin", 0))
    return mins

def _sleep_avg_recent(user_id, k=3):
    vals = []
    cur = db.sensordata.find({"userId": user_id, "metricType": "SleepScore"}).sort("ts", -1).limit(k)
    for d in cur:
        try:
            vals.append(float(d.get("value", 0)))
        except:
            pass
    return round(sum(vals)/len(vals), 1) if vals else 0.0

def _progress_for_goal(user_id, g):
    t = float(g.get("target", 0))
    kind = g.get("type")
    if kind == "steps_daily":
        got = _steps_today(user_id); unit = "steps"
    elif kind == "active_minutes_daily":
        got = _active_minutes_today_from_plan(user_id); unit = "min"
    elif kind == "sleep_score_avg":
        got = _sleep_avg_recent(user_id, 3); unit = "score"
    else:
        got = 0; unit = ""
    pct = 0 if t <= 0 else min(100, round(got / t * 100))
    return {"value": got, "target": t, "percent": pct, "unit": unit}

@app.get("/me/goals")
@jwt_required(optional=True)
def goals_list():
    user_id = get_user_id()
    try:
        out = []
        for g in db.goals.find({"userId": user_id}).sort("createdAt", -1):
            g = dict(g)
            g["id"] = g.get("id") or str(g["_id"])
            g.pop("_id", None)
            g["progress"] = _progress_for_goal(user_id, g)
            if isinstance(g.get("createdAt"), (datetime, date)):
                g["createdAt"] = g["createdAt"].isoformat()
            out.append(g)
        return jsonify(out)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error": "database_unreachable", "detail": str(e)}), 503

@app.post("/me/goals")
@jwt_required(optional=True)
def goals_create():
    """
    Body: { type: 'steps_daily'|'active_minutes_daily'|'sleep_score_avg',
            target: number, title?: string, deadline?: ISO }
    """
    user_id = get_user_id()
    b = request.json or {}
    gtype = b.get("type")
    target = b.get("target")
    if gtype not in {"steps_daily", "active_minutes_daily", "sleep_score_avg"}:
        return jsonify({"error": "bad_type"}), 400
    try:
        target = float(target)
    except:
        return jsonify({"error": "bad_target"}), 400
    g = {
        "_id": ObjectId(),
        "id": None,
        "userId": user_id,
        "type": gtype,
        "target": target,
        "title": b.get("title", gtype.replace("_", " ").title()),
        "deadline": b.get("deadline"),
        "status": "Active",
        "createdAt": datetime.now(datetime.UTC),
    }
    try:
        g["id"] = str(g["_id"])
        db.goals.insert_one(g)
        g.pop("_id", None)
        g["progress"] = _progress_for_goal(user_id, g)
        if isinstance(g.get("createdAt"), datetime):
            g["createdAt"] = g["createdAt"].isoformat()
        return jsonify(g)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error":"database_unreachable","detail":str(e)}), 503

@app.patch("/me/goals/<gid>")
@jwt_required(optional=True)
def goals_update(gid):
    user_id = get_user_id()
    b = request.json or {}
    updates = {}
    for k in ("title","deadline","status","target"):
        if k in b: updates[k] = b[k]
    if "target" in updates:
        try: updates["target"] = float(updates["target"])
        except: return jsonify({"error":"bad_target"}), 400
    try:
        db.goals.update_one({"userId": user_id, "$or":[{"id":gid},{"_id":ObjectId(gid)}]}, {"$set": updates})
        g = db.goals.find_one({"userId": user_id, "$or":[{"id":gid},{"_id":ObjectId(gid)}]})
        if not g:
            return jsonify({"error":"not_found"}), 404
        g = dict(g); g["id"] = g.get("id") or str(g["_id"]); g.pop("_id", None)
        g["progress"] = _progress_for_goal(user_id, g)
        if isinstance(g.get("createdAt"), datetime): g["createdAt"] = g["createdAt"].isoformat()
        return jsonify(g)
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error":"database_unreachable","detail":str(e)}), 503

@app.delete("/me/goals/<gid>")
@jwt_required(optional=True)
def goals_delete(gid):
    user_id = get_user_id()
    try:
        db.goals.delete_one({"userId": user_id, "$or":[{"id":gid},{"_id":ObjectId(gid)}]})
        return {"ok": True}
    except (PyMongoError, ServerSelectionTimeoutError) as e:
        return jsonify({"error":"database_unreachable","detail":str(e)}), 503

# --- Real-time nudges (SSE) ---
@app.get("/stream/nudges")
@jwt_required(optional=True)
def stream_nudges():
    user_id = get_user_id()
    def event_stream():
        while True:
            time.sleep(15)
            yield f"data: {json.dumps({'userId': user_id, 'message': 'Stand up and stretch for 1–2 minutes.'})}\n\n"
    return Response(event_stream(), mimetype="text/event-stream")

# ----------------- main -----------------
if __name__ == "__main__":
    if (MONGO_URI.startswith("mongodb+srv://") or "mongodb.net" in MONGO_URI) and not _CERT_PATH:
        logger.warning("Using MongoDB Atlas but 'certifi' is not installed. "
                       "Run 'pip install certifi' to avoid TLS errors.")
    app.run(host="0.0.0.0", port=5000)
