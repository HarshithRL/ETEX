import { useState } from "react";
import { useNavigate } from "react-router-dom";

import NewProjectChrome from "./NewProjectChrome";
import ProjectBriefForm from "./ProjectBriefForm";
import { createProject } from "./createProject";
import { NEW_PROJECT_PATH } from "./paths";
import {
  EMPTY_BRIEF,
  EMPTY_REQUIREMENTS,
  canCreateProject,
  createProjectPayload,
} from "./projectFormOptions";
import { useNextProjectCode } from "./useNextProjectCode";
import "./NewProject.css";
import "./NewProjectForm.css";

function NewProjectForm() {
  const navigate = useNavigate();
  const { projectId, loadingProjectId, loadError } = useNextProjectCode();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [brief, setBrief] = useState(EMPTY_BRIEF);
  const [requirements, setRequirements] = useState(EMPTY_REQUIREMENTS);
  const [files, setFiles] = useState([]);

  const formError = error || loadError;
  const canCreate = canCreateProject({
    projectId,
    brief,
    submitting,
    loadingProjectId,
  });

  function updateBrief(field, value) {
    setBrief((current) => ({ ...current, [field]: value }));
  }

  async function handleCreate() {
    if (!canCreate) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createProject(
        createProjectPayload(projectId, brief, requirements),
        files,
      );
      navigate(created.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create project.");
      setSubmitting(false);
    }
  }

  return (
    <NewProjectChrome
      crumbs={[
        { label: "New project", to: NEW_PROJECT_PATH },
        { label: "Form" },
      ]}
    >
      <header className="new-project-form-header">
        <span className="new-project-eyebrow">CREATE A SOURCING PROJECT</span>
        <h1>Fill the brief manually</h1>
        <p>
          Enter project details and stage vendor files. Creating the project
          opens the workspace where the knowledge graph is built.
        </p>
      </header>

      <ProjectBriefForm
        projectId={projectId}
        loadingProjectId={loadingProjectId}
        brief={brief}
        onUpdateBrief={updateBrief}
        requirements={requirements}
        onRequirementsChange={setRequirements}
        files={files}
        onFilesChange={setFiles}
        footer={
          <>
            {formError ? <p className="new-project-error">{formError}</p> : null}
            <button
              className="primary-button new-project-create"
              type="button"
              disabled={!canCreate}
              onClick={handleCreate}
            >
              {submitting ? "Creating…" : "Create New Project"}
            </button>
            <p className="new-project-offers-hint">
              Creates the project session and stores your files. Build the
              knowledge graph from the workspace.
            </p>
          </>
        }
      />
    </NewProjectChrome>
  );
}

export default NewProjectForm;
