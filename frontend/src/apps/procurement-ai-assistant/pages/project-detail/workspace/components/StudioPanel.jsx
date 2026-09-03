import { useCallback, useEffect, useState } from "react";

import { apiGet, apiPost } from "../../../../../../services/api";

const STUDIO_TABS = ["Analysis", "Evidence", "Context", "Graph"];
const API_HOST = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
const API_BASE = `http://${API_HOST}:5000`;

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
          <text key={label.text} x={label.x} y={label.y} className="ws-graph-label">
            {label.text}
          </text>
        ))}
      </svg>
      {graph.nodes.map((node) => (
        <div key={node.id} className={`ws-graph-node ${node.className}`}>
          {node.labelKey === "projectName" ? projectName : node.label}
        </div>
      ))}
    </div>
  );
}

function HitlRail({ insights, skippedGaps, busy, onSkipGaps, onBuild, onAddFile }) {
  const decision = insights?.decision || {};
  const packs = insights?.packs || {};
  const missing = (insights?.requirements?.items || []).filter((item) => item.status === "missing");
  const xlsxReady = packs.xlsx?.status === "ready";
  const pptReady = packs.ppt?.status === "ready";

  let step = "upload";
  if ((insights?.file_count || 0) > 0) step = "kb";
  if ((insights?.parsed_ok || 0) > 0 || (insights?.file_count || 0) > 0) step = "gaps";
  if (skippedGaps || missing.length === 0) step = "xlsx";
  if (xlsxReady) step = "ppt";
  if (pptReady) step = "done";

  const steps = [
    { id: "upload", label: "Create + files" },
    { id: "kb", label: "Knowledge base" },
    { id: "gaps", label: "Missing docs" },
    { id: "xlsx", label: "Comparison Excel" },
    { id: "ppt", label: "SteerCo PPT" },
  ];
  const currentIndex = ["upload", "kb", "gaps", "xlsx", "ppt", "done"].indexOf(step);

  return (
    <div className="ws-hitl">
      <ol className="ws-hitl-steps">
        {steps.map((item, index) => {
          let className = "";
          if (index < currentIndex) className = "done";
          else if (step === "done" && index === steps.length - 1) className = "done";
          else if (index === currentIndex) className = "current";
          return (
            <li key={item.id} className={className}>
              <span>{index + 1}</span>
              {item.label}
            </li>
          );
        })}
      </ol>

      {step === "gaps" && missing.length > 0 && (
        <article className="ws-insight-card pack">
          <header>
            <span>HITL</span>
            <strong>{missing.length} missing</strong>
          </header>
          <p>Upload the remaining files, or continue with gaps marked missing. Packs stay draft.</p>
          <ul className="ws-gap-list">
            {missing.map((item) => (
              <li key={item.checklist_key} className="block">
                <span>{item.label}</span>
                <em>missing</em>
              </li>
            ))}
          </ul>
          <div className="ws-pack-actions">
            <button type="button" className="ws-pack-btn" onClick={onAddFile}>
              Upload remaining
            </button>
            <button type="button" className="ws-pack-link" onClick={onSkipGaps}>
              Continue with gaps
            </button>
          </div>
        </article>
      )}

      {step === "xlsx" && !xlsxReady && (
        <article className="ws-insight-card pack">
          <header>
            <span>Permission</span>
            <strong>Excel</strong>
          </header>
          <p>{decision.summary || "Build the comparison matrix from parsed files. Humans award."}</p>
          <div className="ws-pack-actions">
            <button type="button" className="ws-pack-btn" disabled={busy === "xlsx"} onClick={() => onBuild("xlsx")}>
              {busy === "xlsx" ? "Building\u2026" : "Yes \u2014 build comparison"}
            </button>
          </div>
        </article>
      )}

      {xlsxReady && !pptReady && (
        <article className="ws-insight-card pack">
          <header>
            <span>Permission</span>
            <strong>SteerCo</strong>
          </header>
          <p>Review the Excel first. PPT numbers come only from named Excel fields.</p>
          <div className="ws-pack-actions">
            {packs.xlsx?.href && (
              <a className="ws-pack-link" href={`${API_BASE}${packs.xlsx.href}`}>
                Review Excel
              </a>
            )}
            <button type="button" className="ws-pack-btn" disabled={busy === "ppt"} onClick={() => onBuild("ppt")}>
              {busy === "ppt" ? "Building\u2026" : "Yes \u2014 build SteerCo"}
            </button>
          </div>
        </article>
      )}

      {pptReady && packs.ppt?.href && (
        <article className="ws-insight-card pack">
          <header>
            <span>Ready</span>
            <strong>Packs</strong>
          </header>
          <div className="ws-pack-actions">
            <a className="ws-pack-link" href={`${API_BASE}${packs.xlsx.href}`}>
              Download Excel
            </a>
            <a className="ws-pack-link" href={`${API_BASE}${packs.ppt.href}`}>
              Download PPT
            </a>
          </div>
        </article>
      )}
    </div>
  );
}

function StudioPanel({ projectId, projectName, graph, fileTick, onAddFile }) {
  const [tab, setTab] = useState("Analysis");
  const [insights, setInsights] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState("");
  const [skippedGaps, setSkippedGaps] = useState(false);

  const refresh = useCallback(() => {
    if (!projectId) return undefined;
    return apiGet(`/api/procurement/projects/${projectId}/insights`)
      .then((payload) => {
        setInsights(payload);
        setError(null);
      })
      .catch(() => setError("Unable to load analysis."));
  }, [projectId]);

  useEffect(() => {
    refresh();
  }, [refresh, fileTick]);

  useEffect(() => {
    if (!projectId) return undefined;
    const id = window.setInterval(refresh, 4000);
    return () => window.clearInterval(id);
  }, [projectId, refresh]);

  async function onBuild(kind) {
    setBusy(kind);
    try {
      await apiPost(`/api/procurement/projects/${projectId}/packs/${kind}`, {});
      await refresh();
    } catch (err) {
      setError(err?.message || "Pack build failed.");
    } finally {
      setBusy("");
    }
  }

  const evidence = insights?.vendors?.flatMap((vendor) =>
    (vendor.evidence || []).map((item) => ({ vendor: vendor.name, ...item })),
  );

  return (
    <aside className="ws-studio">
      <div className="ws-panel-header">
        <strong>STUDIO</strong>
      </div>
      <div className="ws-studio-tabs">
        {STUDIO_TABS.map((name) => (
          <button key={name} type="button" className={tab === name ? "active" : ""} onClick={() => setTab(name)}>
            {name}
          </button>
        ))}
      </div>
      <div className="ws-studio-body">
        {tab === "Graph" && <KnowledgeGraph projectName={projectName} graph={graph} />}
        {tab === "Context" && (
          <div className="ws-studio-placeholder">
            <p>
              {insights?.process_label || "Process unset"} \u00b7 {insights?.owner_entity || "Owner unset"}
            </p>
            <p className="ws-insight-meta">
              KB {insights?.kb_status || "empty"} \u00b7 {insights?.file_count || 0} files \u00b7 {insights?.knowledge_pct ?? 0}%
            </p>
          </div>
        )}
        {tab === "Evidence" && (
          <div className="ws-insight-list">
            {(evidence || []).length === 0 ? (
              <div className="ws-studio-placeholder">
                <p>Cited snippets appear after parse. No locator means missing, not zero.</p>
              </div>
            ) : (
              evidence.map((item) => (
                <article key={`${item.chunk_id}-${item.locator}`} className="ws-insight-card">
                  <header>
                    <span>{item.vendor}</span>
                    <strong>{item.locator}</strong>
                  </header>
                  <p>{item.quote || "No quote on this chunk."}</p>
                </article>
              ))
            )}
          </div>
        )}
        {tab === "Analysis" && (
          <div className="ws-insight-list">
            {error && <p className="ws-insight-meta">{error}</p>}
            <article className="ws-insight-card">
              <header>
                <span>Process</span>
                <strong>{insights?.process_label || "Unset"}</strong>
              </header>
              <p>
                {insights?.owner_entity || "Owner unset"}
                {" · "}
                {insights?.file_count || 0} files
                {" · "}
                {insights?.knowledge_pct ?? 0}% coverage
              </p>
            </article>
            <HitlRail
              insights={insights}
              skippedGaps={skippedGaps}
              busy={busy}
              onSkipGaps={() => setSkippedGaps(true)}
              onBuild={onBuild}
              onAddFile={onAddFile}
            />
            {(insights?.vendors || []).map((vendor) => (
              <article key={vendor.vendor_id} className="ws-insight-card">
                <header>
                  <span>Vendor</span>
                  <strong>{vendor.name}</strong>
                </header>
                <p>{vendor.headline}</p>
              </article>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

export default StudioPanel;
