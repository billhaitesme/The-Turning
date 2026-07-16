export default function PanelShell({ title, accent, children, lamp, activityAt }) {
  return (
    <section className="panel-shell" style={{ borderColor: accent }}>
      <header className="panel-head">
        <div className="panel-title-wrap">
          <span className="panel-title">{title}</span>
          {activityAt ? <span className="panel-activity">ACTIVITY {activityAt}</span> : null}
        </div>
        {lamp}
      </header>
      <div className="panel-content">{children}</div>
    </section>
  );
}
