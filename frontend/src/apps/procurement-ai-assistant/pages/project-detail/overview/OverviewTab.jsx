import { useEffect, useState } from "react";
import { apiGet } from "../../../../../services/api";
import "./overview-tab.css";

function ProgressRing({ value }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="progress-ring" aria-label={`${value}% complete`}>
      <svg viewBox="0 0 140 140" width="140" height="140">
        <circle className="progress-ring-track" cx="70" cy="70" r={radius} />
        <circle
          className="progress-ring-value"
          cx="70"
          cy="70"
          r={radius}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="progress-ring-label">
        <strong>{value}%</strong>
        <span>Complete</span>
      </div>
    </div>
  );
}

function OverviewTab({ projectId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setError(null);
    apiGet(`/api/procurement/projects/${projectId}/overview`)
      .then(setData)
      .catch(() => setError("Unable to load overview."));
  }, [projectId]);

  if (!data && !error) {
    return <div className="overview-tab">Loading…</div>;
  }

  if (error || !data) {
    return <div className="overview-tab">{error ?? "Overview unavailable."}</div>;
  }

  const project = data.project;

  return (
    <div className="overview-tab">
      <div className="overview-grid">
        <section className="overview-card overview-card-progress">
          <div className="overview-card-head">
            <h2>Project Progress</h2>
            <span>{project.code}</span>
          </div>
          <div className="progress-body">
            <ProgressRing value={project.progress} />
            <ul className="progress-stages">
              {data.stages.map((stage) => (
                <li
                  key={stage.name}
                  className={
                    stage.done
                      ? "done"
                      : stage.current
                        ? "current"
                        : ""
                  }
                >
                  <span className="stage-dot" />
                  {stage.name}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="overview-card overview-card-metrics">
          <div className="overview-card-head">
            <h2>Key Metrics</h2>
          </div>
          <div className="metrics-grid">
            {data.metrics.map((metric) => (
              <div key={metric.label} className="metric-tile">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>Upcoming Milestones</h2>
          </div>
          <ul className="milestone-list">
            {data.milestones.map((item) => (
              <li key={item.title}>
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.date}</span>
                </div>
                <em className={`milestone-status ${item.status.toLowerCase().replace(/\s+/g, "-")}`}>
                  {item.status}
                </em>
              </li>
            ))}
          </ul>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>AI Insights</h2>
          </div>
          <ul className="insight-list">
            {data.insights.map((insight) => (
              <li key={insight.title} className={`insight-${insight.type}`}>
                <strong>{insight.title}</strong>
                <p>{insight.body}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>Requirements</h2>
          </div>
          <div className="stat-row">
            <div>
              <span>Total</span>
              <strong>{data.requirements.total}</strong>
            </div>
            <div>
              <span>Approved</span>
              <strong>{data.requirements.approved}</strong>
            </div>
            <div>
              <span>Pending</span>
              <strong>{data.requirements.pending}</strong>
            </div>
            <div>
              <span>Rejected</span>
              <strong>{data.requirements.rejected}</strong>
            </div>
          </div>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>Vendors</h2>
          </div>
          <div className="stat-row">
            <div>
              <span>Invited</span>
              <strong>{data.vendors.invited}</strong>
            </div>
            <div>
              <span>Responded</span>
              <strong>{data.vendors.responded}</strong>
            </div>
            <div>
              <span>Shortlisted</span>
              <strong>{data.vendors.shortlisted}</strong>
            </div>
          </div>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>Documents & Artifacts</h2>
          </div>
          <div className="doc-type-row">
            <span className="doc-chip pdf">PDF {data.documents.pdf}</span>
            <span className="doc-chip docx">DOCX {data.documents.docx}</span>
            <span className="doc-chip xlsx">XLSX {data.documents.xlsx}</span>
          </div>
          <ul className="recent-docs">
            {data.documents.recent.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </section>

        <section className="overview-card">
          <div className="overview-card-head">
            <h2>Tasks & Approvals</h2>
          </div>
          <ul className="approval-list">
            {data.approvals.map((item) => (
              <li key={item.title}>
                <div>
                  <strong>{item.title}</strong>
                  <span>{item.owner}</span>
                </div>
                <em className={`approval-status ${item.status.toLowerCase()}`}>
                  {item.status}
                </em>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="overview-quick-actions">
        <div className="overview-card-head">
          <h2>Quick Actions</h2>
        </div>
        <div className="quick-action-row">
          {data.quickActions.map((action) => (
            <button key={action} type="button" className="quick-action-btn">
              {action}
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

export default OverviewTab;
