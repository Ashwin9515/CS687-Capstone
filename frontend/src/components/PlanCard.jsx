export default function PlanCard({ plan, onComplete }) {
  if (!plan) return null
  return (
    <div className="card">
      <h3>Today’s Plan — {plan.date}</h3>
      <ul>
        {plan.items?.map((i, idx)=>(
          <li key={idx}>
            <strong>{i.type}</strong> • {i.intensity} • {i.durationMin} min — {i.notes}
          </li>
        ))}
      </ul>
      <div className="row">
        <button onClick={onComplete}>Mark Complete</button>
      </div>
      <p className="status">Status: {plan.status}</p>
    </div>
  )
}
