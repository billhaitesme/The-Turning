import { useMemo, useState } from "react";

const MAP = {
  A: "AUR-A", B: "AUR-B", C: "AUR-C", D: "AUR-D", E: "AUR-E", F: "AUR-F", G: "AUR-G",
  H: "AUR-H", I: "AUR-I", J: "AUR-J", K: "AUR-K", L: "AUR-L", M: "AUR-M", N: "AUR-N",
  O: "AUR-O", P: "AUR-P", Q: "AUR-Q", R: "AUR-R", S: "AUR-S", T: "AUR-T", U: "AUR-U",
  V: "AUR-V", W: "AUR-W", X: "AUR-X", Y: "AUR-Y", Z: "AUR-Z",
};

export default function AurebeshTranslator() {
  const [input, setInput] = useState("BRIDGE ZERO");

  const output = useMemo(() => {
    return String(input || "")
      .toUpperCase()
      .split("")
      .map((ch) => (MAP[ch] ? MAP[ch] : ch))
      .join(" ");
  }, [input]);

  return (
    <div className="instrument translator">
      <div className="engraved-label">Aurebesh Utility</div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className="translator-input"
        placeholder="Enter text"
      />
      <div className="translator-output">{output}</div>
    </div>
  );
}
