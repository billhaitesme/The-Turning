import { useState } from "react";

// Real Aurebesh via the bundled OFL font (SilvinoR). The font maps each Latin
// letter to its Aurebesh glyph, so the operator types normally and reads Aurebesh.
export default function AurebeshTranslator() {
  const [input, setInput] = useState("BRIDGE ZERO");

  return (
    <div className="instrument translator">
      <div className="engraved-label">Aurebesh Utility</div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className="translator-input"
        placeholder="Enter text"
      />
      <div className="translator-output" aria-label={`Aurebesh: ${input}`}>
        {input}
      </div>
      <div className="translator-roman">{input.toUpperCase()}</div>
    </div>
  );
}
