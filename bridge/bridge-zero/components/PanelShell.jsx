export default function PanelShell({ title, accent, children, lamp }) {
  return (
    <section className="panel-shell" style={{ borderColor: accent }}>
      <header className="panel-head">
        <div className="panel-title-wrap">
          <span className="panel-title">{title}</span>
        </div>
        {lamp}
      </header>
      <div className="panel-content">{children}</div>
    </section>
  );
}
