import { useState } from "react";

const STUDIO_TABS = ["Context", "Evidence", "Graph", "Analysis"];

function KnowledgeGraph({ projectName, graph }) {
  return (
    <div className="ws-graph">
      <svg viewBox="0 0 360 320" className="ws-graph-svg" aria-hidden="true">
        {graph.edges.map((edge, index) => (
          <line
            key={`edge-${index}`}
            x1={edge.x1}
            y1={edge.y1}
            x2={edge.x2}
            y2={edge.y2}
            className="ws-graph-edge"
          />
        ))}

        {graph.edgeLabels.map((label) => (
          <text
            key={label.text}
            x={label.x}
            y={label.y}
            className="ws-graph-label"
          >
            {label.text}
          </text>
        ))}
      </svg>

      {graph.nodes.map((node) => (
        <div
          key={node.id}
          className={`ws-graph-node ${node.className}`}
        >
          {node.labelKey === "projectName" ? projectName : node.label}
        </div>
      ))}
    </div>
  );
}

function StudioPanel({ projectName, graph }) {
  const [tab, setTab] = useState("Graph");

  return (
    <aside className="ws-studio">
      <div className="ws-panel-header">
        <strong>STUDIO</strong>
      </div>

      <div className="ws-studio-tabs">
        {STUDIO_TABS.map((name) => (
          <button
            key={name}
            type="button"
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>

      <div className="ws-studio-body">
        {tab === "Graph" && (
          <KnowledgeGraph projectName={projectName} graph={graph} />
        )}
        {tab === "Context" && (
          <div className="ws-studio-placeholder">
            <p>Project context and selected files will appear here.</p>
          </div>
        )}
        {tab === "Evidence" && (
          <div className="ws-studio-placeholder">
            <p>Evidence snippets cited by the AI will appear here.</p>
          </div>
        )}
        {tab === "Analysis" && (
          <div className="ws-studio-placeholder">
            <p>Structured analysis results will appear here.</p>
          </div>
        )}
      </div>
    </aside>
  );
}

export default StudioPanel;
