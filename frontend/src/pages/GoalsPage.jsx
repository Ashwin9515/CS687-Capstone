import { useEffect, useState } from "react";
import { getGoals, createGoal, updateGoal, deleteGoal } from "../api";

function GoalRow({ g, onComplete, onDelete }) {
  const p = g.progress || { percent: 0, value: 0, target: 0, unit: "" };
  return (
    <div className="card" style={{display:'grid', gap:'.4rem'}}>
      <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
        <h3 style={{margin:0}}>{g.title}</h3>
        <small className="muted">{g.type.replaceAll('_',' ')}</small>
      </div>
      <div className="muted">{p.value} / {p.target} {p.unit}</div>
      <div className="progress">
        <div className="progress-bar" style={{width:`${p.percent}%`}} />
      </div>
      <div className="row" style={{gap:'.5rem'}}>
        <button className="btn" onClick={onComplete} disabled={g.status === 'Completed'}>
          {g.status === 'Completed' ? 'Completed' : 'Mark Complete'}
        </button>
        <button className="btn subtle" onClick={onDelete}>Delete</button>
      </div>
    </div>
  );
}

export default function GoalsPage() {
  const [goals, setGoals] = useState([]);
  const [type, setType] = useState("steps_daily");
  const [target, setTarget] = useState("");
  const [title, setTitle] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try { setGoals(await getGoals()); }
    catch (e) { console.error(e); setErr("Failed to load goals"); }
  };

  useEffect(() => { load(); }, []);

  const add = async () => {
    try {
      const payload = { type, target: Number(target), title };
      if (!payload.target) return;
      await createGoal(payload);
      setTarget(""); setTitle("");
      await load();
    } catch (e) { console.error(e); setErr("Failed to create goal"); }
  };

  return (
    <div className="container">
      <header className="hero">
        <h1>Set <span className="accent">Goals</span></h1>
        <p>Create daily and weekly targets and see your live progress.</p>
      </header>

      {err && <div className="card error"><strong>Error:</strong> {err}</div>}

      <div className="card" style={{display:'grid', gap:'.5rem'}}>
        <h3>Create a Goal</h3>
        <div className="row" style={{gap:'.5rem', alignItems:'center', flexWrap:'wrap'}}>
          <select value={type} onChange={e=>setType(e.target.value)} style={{padding:'.5rem'}}>
            <option value="steps_daily">Daily Steps</option>
            <option value="active_minutes_daily">Daily Active Minutes</option>
            <option value="sleep_score_avg">Sleep Score (avg of 3)</option>
          </select>
          <input
            type="number"
            value={target}
            onChange={e=>setTarget(e.target.value)}
            placeholder="Target (e.g., 8000)"
            style={{padding:'.5rem', border:'1px solid #e2e8f0', borderRadius:'10px', width:'200px'}}
          />
          <input
            value={title}
            onChange={e=>setTitle(e.target.value)}
            placeholder="Optional title"
            style={{padding:'.5rem', border:'1px solid #e2e8f0', borderRadius:'10px', width:'240px'}}
          />
          <button className="btn" onClick={add}>Add Goal</button>
          <a className="btn subtle" href="/" style={{textDecoration:'none'}}>← Back to Dashboard</a>
        </div>
      </div>

      <section className="grid" style={{marginTop:'.75rem'}}>
        {goals.map(g =>
          <GoalRow
            key={g.id}
            g={g}
            onComplete={async ()=>{ await updateGoal(g.id, {status:'Completed'}); await load(); }}
            onDelete={async ()=>{ await deleteGoal(g.id); await load(); }}
          />
        )}
      </section>
    </div>
  );
}
