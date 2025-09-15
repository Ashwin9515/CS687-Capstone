// src/pages/WeekPlannerPage.jsx
import { useEffect, useMemo, useState } from "react";
import {
  getWeekPlan,
  regenerateWeekPlan,
  startPlanOnDate,
  completePlanOnDate,
} from "../api";

function DayCard({ plan, onStart, onComplete }) {
  const dateLabel = useMemo(() => {
    try {
      const d = new Date(plan.date);
      return d.toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
      });
    } catch {
      return plan.date;
    }
  }, [plan.date]);

  const items = plan.items || [];
  const workouts = items.filter((i) => i.type === "Workout");
  const meals = items.filter((i) => i.type === "Meal");

  const inProgress = plan.status === "In Progress";
  const completed = plan.status === "Completed";

  return (
    <div className="card">
      <div
        className="row"
        style={{ justifyContent: "space-between", alignItems: "baseline" }}
      >
        <h3 style={{ margin: 0 }}>{dateLabel}</h3>
        <small className="muted">{plan.status || "Scheduled"}</small>
      </div>

      {workouts.length > 0 && (
        <>
          <div className="muted" style={{ marginTop: ".25rem" }}>
            Workouts
          </div>
          <ul style={{ marginTop: ".25rem" }}>
            {workouts.map((w, i) => (
              <li key={i}>
                {w.name || w.title || "Workout"} • {w.durationMin || 20} min
              </li>
            ))}
          </ul>
        </>
      )}

      {meals.length > 0 && (
        <>
          <div className="muted" style={{ marginTop: ".5rem" }}>
            Meals
          </div>
          <ul style={{ marginTop: ".25rem" }}>
            {meals.map((m, i) => (
              <li key={i}>{m.name || m.title}</li>
            ))}
          </ul>
        </>
      )}

      <div className="row" style={{ marginTop: ".6rem", gap: ".5rem" }}>
        <button
          className="btn"
          onClick={onStart}
          disabled={inProgress || completed}
          title={completed ? "Already completed" : inProgress ? "Already started" : "Start plan"}
        >
          {inProgress ? "In Progress" : completed ? "Completed" : "Start"}
        </button>
        <button className="btn subtle" onClick={onComplete}>
          Mark Complete
        </button>
      </div>
    </div>
  );
}

export default function WeekPlannerPage() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    setLoading(true);
    try {
      const p = await getWeekPlan();
      setPlans(Array.isArray(p) ? p : []);
    } catch (e) {
      console.error(e);
      setErr("Failed to load weekly plan");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleStart = async (iso) => {
    try {
      await startPlanOnDate(iso);
      await load();
    } catch (e) {
      console.error(e);
      setErr("Failed to start plan");
    }
  };

  const handleComplete = async (iso) => {
    try {
      await completePlanOnDate(iso);
      await load();
    } catch (e) {
      console.error(e);
      setErr("Failed to complete plan");
    }
  };

  return (
    <div className="container">
      <header className="hero">
        <h1>
          Plan <span className="accent">Week</span>
        </h1>
        <p>View and manage your next 7 days.</p>
      </header>

      {err && (
        <div className="card error">
          <strong>Error:</strong> {err}
        </div>
      )}

      <div className="row" style={{ gap: ".5rem", marginBottom: ".75rem" }}>
        <button className="btn" onClick={load}>
          Refresh
        </button>
        <button
          className="btn"
          onClick={async () => {
            await regenerateWeekPlan();
            await load();
          }}
        >
          Regenerate All 7 Days
        </button>
        <a className="btn subtle" href="/" style={{ textDecoration: "none" }}>
          ← Back to Dashboard
        </a>
      </div>

      {loading ? (
        <div className="card">Loading…</div>
      ) : (
        <section
          className="grid"
          style={{ gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))" }}
        >
          {plans.map((p) => (
            <DayCard
              key={p.date}
              plan={p}
              onStart={() => handleStart(p.date)}
              onComplete={() => handleComplete(p.date)}
            />
          ))}
        </section>
      )}
    </div>
  );
}
