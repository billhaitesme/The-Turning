export default function ConsoleButton({ label, onClick, disabled = false }) {
  return (
    <button type="button" className="console-button" onClick={onClick} disabled={disabled}>
      {label}
    </button>
  );
}
