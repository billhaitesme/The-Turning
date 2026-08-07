export default function DependencyGraph({ nodes = [] }) {
  return (
    <div className="instrument dependency-graph">
      <div className="engraved-label">Dependency Graph</div>
      <div className="dependency-lines">
        {nodes.map((node) => (
          <div className="dependency-node" key={node.id}>
            <span className={`dep-state ${node.status}`}>{node.status.toUpperCase()}</span>
            <span className="dep-title">{node.title}</span>
            <span className="dep-next">{node.dependsOn || "root"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
