import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet } from "../../../../services/api";
import OverviewTab from "./overview/OverviewTab";
import WorkspaceTab from "./workspace/WorkspaceTab";
import DocumentsTab from "./documents/DocumentsTab";
import "./project-detail.css";

function ProjectDetail() {
  const { projectId } = useParams();
  const [activeTab, setActiveTab] = useState("overview");
  const [shell, setShell] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setShell(null);
    setError(null);
    apiGet(`/api/procurement/projects/${projectId}`)
      .then(setShell)
      .catch(() => setError("Unable to load project."));
  }, [projectId]);

  if (!shell && !error) {
    return (
      <div className="project-detail-page">
        <div className="project-detail-container">Loading…</div>
      </div>
    );
  }

  if (error || !shell) {
    return (
      <div className="project-detail-page">
        <div className="project-detail-container">
          {error ?? "Project not found."}
        </div>
      </div>
    );
  }

  const { project, tabs } = shell;

  return (
    <div
      className={`project-detail-page${activeTab === "workspace" ? " is-workspace" : ""}`}
    >
      <div
        className={`project-detail-container${activeTab === "workspace" ? " is-workspace" : ""}`}
      >
        <div className="project-breadcrumb">
          <Link to="/app/procurement-ai-assistant/projects">Projects</Link>
          <span>›</span>
          <strong>{project.name}</strong>
        </div>

        <header className="project-detail-header">
          <div>
            <span className="project-detail-eyebrow">
              PROCUREMENT PROJECT
            </span>

            <h1>{project.name}</h1>

            <div className="project-meta">
              <span className="project-status-badge">{project.status}</span>
              <span>{project.code}</span>
              <span>•</span>
              <span>Owner: {project.owner}</span>
              <span>•</span>
              <span>Created {project.created}</span>
              <span>•</span>
              <span>Deadline {project.deadline}</span>
            </div>
          </div>

          <div className="project-header-actions">
            <button type="button" className="secondary-button">
              Export
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setActiveTab("workspace")}
            >
              Open Workspace
            </button>
            <button type="button" className="primary-button">
              + Upload Files
            </button>
          </div>
        </header>

        <nav className="project-tabs" aria-label="Project sections">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`project-tab${activeTab === tab.id ? " active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="project-tab-body">
          {activeTab === "overview" && (
            <OverviewTab projectId={projectId} />
          )}
          {activeTab === "workspace" && (
            <WorkspaceTab projectId={projectId} />
          )}
          {activeTab === "documents" && (
            <DocumentsTab projectId={projectId} />
          )}
          {activeTab === "requirements" && (
            <section className="project-tab-placeholder">
              <p>Requirements for this project will appear here.</p>
            </section>
          )}
          {activeTab === "vendors" && (
            <section className="project-tab-placeholder">
              <p>Vendor shortlist and responses will appear here.</p>
            </section>
          )}
          {activeTab === "activity" && (
            <section className="project-tab-placeholder">
              <p>Recent project activity will appear here.</p>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProjectDetail;
