export default function StatCard({ title, value, sub="", icon=null, gradient="g1" }) {
  return (
    <div className={`stat ${gradient}`}>
      <div className="stat-top">
        <span className="stat-title">{title}</span>
        {icon && <span className="stat-icon">{icon}</span>}
      </div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}
