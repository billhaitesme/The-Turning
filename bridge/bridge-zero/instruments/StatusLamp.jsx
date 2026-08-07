import { statusColors } from "../themes/bridgeZeroTheme";

export default function StatusLamp({ state = "OFFLINE", label }) {
  const color = statusColors[state] || statusColors.OFFLINE;
  const isBusy = state === "BUSY";
  return (
    <div className="instrument status-lamp-wrap">
      <div className="engraved-label">{label}</div>
      <div className="status-lamp-row">
        <span
          className={`status-lamp ${isBusy ? "pulse" : ""}`}
          style={{ backgroundColor: color, boxShadow: `0 0 9px ${color}` }}
          aria-label={`${label} ${state}`}
        />
        <span className="status-lamp-state">{state}</span>
      </div>
    </div>
  );
}
