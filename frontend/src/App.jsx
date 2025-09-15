import { useEffect, useMemo, useState } from "react";

import {
  login, getPlan, completePlan, getRecs, makeNudge,
  ingest, listMetrics, setSteps
} from "./api";

import PlanCard from "./components/PlanCard";
import StatCard from "./components/StatCard";
import AskCoach from "./components/AskCoach";

function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }
function avg(arr) { return arr.length ? Math.round(arr.reduce((a,b)=>a+b,0)/arr.length) : 0; }

export default function App() {
  const [plan, setPlan]       = useState(null);
  const [recs, setRecs]       = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr]         = useState(null);

  // steps form
  const [stepsInput, setStepsInput] = useState("");

  const refresh = async () => {
    setErr(null); setLoading(true);
    try {
      await login();
      const [p, r, m] = await Promise.all([getPlan(), getRecs(), listMetrics()]);
      setPlan(p); setRecs(r); setMetrics(m);
    } catch (e) {
      console.error(e);
      setErr("Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  // ---- derived stats ----
  const nowISODate = new Date().toISOString().slice(0, 10);

  const stepsToday = useMemo(() =>
    metrics
      .filter(m => m.metricType === "Steps" && m.ts.slice(0,10) === nowISODate)
      .reduce((s, m) => s + Number(m.value || 0), 0)
  , [metrics]);

  const hrAvg    = useMemo(() => avg(metrics.filter(m=>m.metricType==="HR").map(m=>Number(m.value||0))), [metrics]);
  const sleepAvg = useMemo(() => avg(metrics.filter(m=>m.metricType==="SleepScore").map(m=>Number(m.value||0))), [metrics]);

  const activeMinutes = useMemo(() =>
    (plan?.items || [])
      .filter(i => i.type === "Workout")
      .reduce((s, i) => s + (Number(i.durationMin) || 0), 0)
  , [plan]);

  const wellness = useMemo(() => {
    const s  = clamp(stepsToday / 100, 0, 100); // 10k steps ~ 100
    const a  = clamp(activeMinutes * 2, 0, 100); // 50 min ~ 100
    const sl = clamp(sleepAvg, 0, 100);          // already 0–100
    return Math.round(0.3*s + 0.2*a + 0.5*sl);
  }, [stepsToday, activeMinutes, sleepAvg]);

  const addSample = async () => {
    try {
      await ingest("HR", 68 + Math.floor(Math.random()*18));
      await ingest("Steps", 800 + Math.floor(Math.random()*1800));
      if (Math.random() < 0.4) await ingest("SleepScore", 65 + Math.floor(Math.random()*25));
      setMetrics(await listMetrics());
    } catch (e) {
      console.error(e); setErr("Failed to add metrics");
    }
  };

  const saveSteps = async () => {
    try {
      const v = parseInt(stepsInput || "0", 10);
      if (Number.isNaN(v) || v < 0) return;
      await setSteps(v);
      setMetrics(await listMetrics());
      setStepsInput("");
    } catch (e) {
      console.error(e); setErr("Failed to save steps");
    }
  };

  if (loading) return <div className="container"><p>Loading…</p></div>;

  return (
    <div className="container">
      <header className="hero">
        <h1>AI-Powered <span className="accent">Wellness</span></h1>
        <p>Your personalized fitness tracker with daily wellness generation. Smart coaching powered by AI and real-time biometric data.</p>
        <div className="hero-bg" aria-hidden />
      </header>

      {err && <div className="card error"><strong>Error:</strong> {err}</div>}

      {/* STAT STRIP */}
      <section className="stats">
        <StatCard title="Steps Today" value={stepsToday.toLocaleString()} sub="+ live" gradient="g1" />
        <StatCard title="Avg Heart Rate" value={`${hrAvg || 0} BPM`} sub={hrAvg ? "—" : "No data"} gradient="g2" />
        <StatCard title="Active Minutes" value={`${activeMinutes} min`} sub="From today’s plan" gradient="g3" />
        <StatCard title="Sleep Quality" value={`${sleepAvg || 0}%`} sub="Avg recent" gradient="g4" />
      </section>

      {/* WELLNESS + QUICK ACTIONS */}
      <section className="wellness-row">
        <div className="wellness-card">
          <div className="ring">
            <svg viewBox="0 0 120 120" className="ring-svg">
              <circle cx="60" cy="60" r="52" className="ring-bg" />
              <circle
                cx="60" cy="60" r="52"
                className="ring-fg"
                style={{ strokeDasharray: `${(wellness/100)*2*Math.PI*52} ${2*Math.PI*52}` }}
              />
            </svg>
            <div className="ring-center">
              <div className="ring-value">{wellness}</div>
              <div className="ring-label">Wellness Score</div>
            </div>
          </div>
          <div className="ring-caption">
            {wellness >= 80 ? "Excellent Progress!" : wellness >= 60 ? "Great Momentum!" : "Let’s build consistency"}
          </div>
          <button className="btn subtle" onClick={addSample}>Add Sample Metrics</button>
        </div>

        <div className="quick-actions card">
          <h3>Quick Actions</h3>
          <div className="qa-grid">
            {/* Open each tool in a new tab */}
            <button
              className="btn qa start"
              onClick={() => window.open("/workout-videos", "_blank")}
            >
              Workout Videos
              <small>Browse exercise library</small>
            </button>

            <AskCoach />

            <button
              className="btn qa plan"
              onClick={() => window.open("/plan-week", "_blank")}
            >
              Plan Week
              <small>View & regenerate 7 days</small>
            </button>

            <button
              className="btn qa goals"
              onClick={() => window.open("/goals", "_blank")}
            >
              Set Goals
              <small>Create & track targets</small>
            </button>
          </div>
        </div>
      </section>

      {/* PLAN + RECS + METRICS */}
      <section className="grid">
        <PlanCard
          plan={plan}
          onComplete={async () => {
            await completePlan();
            setPlan(await getPlan());
          }}
        />

        <div className="card">
          <h3>Recommendations</h3>
          <button
            className="btn"
            onClick={async () => {
              await makeNudge();
              setRecs(await getRecs());
            }}
          >
            Generate Nudge
          </button>
          <ul>
            {recs.map((r, i) => (
              <li key={i}>
                {r.message} <em>({new Date(r.ts).toLocaleTimeString()})</em>
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <h3>Recent Metrics</h3>
          <button className="btn" onClick={addSample}>Add Sample Metrics</button>

          <div className="row" style={{ marginTop: ".6rem", gap: ".5rem", alignItems: "center" }}>
            <input
              type="number"
              min="0"
              placeholder="Enter steps (e.g. 7500)"
              value={stepsInput}
              onChange={(e) => setStepsInput(e.target.value)}
              style={{ padding: ".5rem .6rem", border: "1px solid #e2e8f0", borderRadius: "10px", width: "200px" }}
            />
            <button className="btn" onClick={saveSteps}>Save Steps</button>
          </div>

          <div className="row" style={{ marginTop: ".6rem" }}>
            <button
              className="btn qa goals"
              onClick={() => window.open("/goals", "_blank")}
            >
              Set Goals
              <small>Create & track targets</small>
            </button>
          </div>

          <ul style={{ marginTop: ".5rem" }}>
            {metrics.slice(0, 12).map((m, i) => (
              <li key={i}>
                {m.metricType}: {m.value}{" "}
                <em>({new Date(m.ts).toLocaleTimeString()})</em>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <footer><small>Coach-free, adaptive wellness • Demo MVP</small></footer>
    </div>
  );
}
