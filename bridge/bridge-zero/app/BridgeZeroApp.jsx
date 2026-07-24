import VersionPlate from "../components/VersionPlate";
import SignalBus from "../instruments/SignalBus";
import ChroniclePanel from "../panels/ChroniclePanel";
import ConversationPanel from "../panels/ConversationPanel";
import DeliberationPanel from "../panels/DeliberationPanel";
import EvidencePanel from "../panels/EvidencePanel";
import IdentityPanel from "../panels/IdentityPanel";
import ModelControlPanel from "../panels/ModelControlPanel";
import PlanningPanel from "../panels/PlanningPanel";
import ReasoningPanel from "../panels/ReasoningPanel";
import ToolsPanel from "../panels/ToolsPanel";
import { getReleaseMetadata } from "./releaseMetadata";
import { useBridgeData } from "./useBridgeData";
import { subsystemColors } from "../themes/bridgeZeroTheme";

const subsystems = ["identity", "evidence", "reasoning", "planning", "deliberation", "tools"];

export default function BridgeZeroApp() {
  const metadata = getReleaseMetadata();
  const bridge = useBridgeData();
  const connectionState = bridge.connection?.state || "INITIALIZING";
  const stale = bridge.connection?.stale;

  return (
    <div className="bridge-root">
      <header className="bridge-header">
        <div className="bridge-brand">
          <div className="brand-title">OMEGA-ARC</div>
          <div className="brand-sub">Bridge Zero</div>
        </div>
        <div className="bridge-status">
          Epoch IX | VERSION 0.2.0 | LINK: {connectionState}{stale ? " | DATA: STALE" : " | DATA: LIVE"}        </div>
      </header>

      <SignalBus subsystems={subsystems} activeSubsystem={bridge.busActive} />

      <div className="bridge-main-grid">
        <section className="bridge-column-left">
          <ConversationPanel accent="#6d90aa" data={bridge.conversation} />
          <div className="panel-grid-two">
            <IdentityPanel accent={subsystemColors.identity} data={bridge.identity} />
            <EvidencePanel accent={subsystemColors.evidence} data={bridge.evidence} />
            <ReasoningPanel accent={subsystemColors.reasoning} data={bridge.reasoning} />
            <PlanningPanel accent={subsystemColors.planning} data={bridge.planning} />
            <DeliberationPanel accent={subsystemColors.deliberation} data={bridge.deliberation} />
            <ToolsPanel
              accent={subsystemColors.tools}
              data={bridge.tools}
              connection={bridge.connection}
            />
          </div>
        </section>

        <section className="bridge-column-right">
          <ModelControlPanel accent="#7aa8c8" data={bridge.modelControl} />
          <VersionPlate metadata={metadata} />
          <ChroniclePanel
            accent="#7c8d9a"
            data={{ state: "READY", record: bridge.chronicleRecord }}
            steps={bridge.chronicleTimeline}
            selected={bridge.selectedChronicle}
            onSelect={bridge.setSelectedChronicle}
          />
        </section>
      </div>
    </div>
  );
}
