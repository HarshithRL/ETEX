import RequirementsEditor from "./RequirementsEditor";
import StagedFileDropzone from "./StagedFileDropzone";
import { BUSINESS_PROCESSES, WORKFLOW_ENTRY_POINTS } from "./projectFormOptions";

const EMPTY_OPTION = "";

function ProjectBriefForm({
  projectId,
  loadingProjectId,
  brief,
  onUpdateBrief,
  requirements,
  onRequirementsChange,
  files,
  onFilesChange,
  footer = null,
}) {
  function updateBrief(field, value) {
    onUpdateBrief(field, value);
  }

  return (
    <div className="new-project-form-grid">
      <section className="new-project-panel" aria-labelledby="purchase-heading">
        <span className="new-project-step">STEP 1 · THE PURCHASE</span>
        <h2 id="purchase-heading">Describe what you are buying</h2>
        <p className="new-project-panel-copy">
          The brief becomes the requirement side of the knowledge graph. Every
          vendor claim is scored against these lines.
        </p>

        <div className="new-project-fields">
          <label className="new-project-field-wide">
            <span>PROJECT NAME</span>
            <input
              value={brief.name}
              onChange={(event) => updateBrief("name", event.target.value)}
              placeholder="e.g. France — screw & fastener selection"
              required
            />
          </label>

          <label>
            <span>CATEGORY</span>
            <input
              value={brief.category}
              onChange={(event) => updateBrief("category", event.target.value)}
              placeholder="Fasteners / mechanical fixings"
            />
          </label>

          <label>
            <span>REGION & SITES</span>
            <input
              value={brief.region}
              onChange={(event) => updateBrief("region", event.target.value)}
              placeholder="France - 6 plants"
            />
          </label>

          <label>
            <span>TARGET SPEND (3 YR, €)</span>
            <input
              value={brief.targetSpend}
              onChange={(event) => updateBrief("targetSpend", event.target.value)}
              placeholder="4200000"
              inputMode="decimal"
            />
          </label>

          <label>
            <span>AWARD HORIZON</span>
            <input
              value={brief.awardHorizon}
              onChange={(event) => updateBrief("awardHorizon", event.target.value)}
              placeholder="36 months, 12-month price lock"
            />
          </label>

          <label className="new-project-field-wide">
            <span>WHAT WE ARE BUYING</span>
            <textarea
              value={brief.description}
              onChange={(event) => updateBrief("description", event.target.value)}
              placeholder="Describe what you're sourcing, quantities, and key constraints…"
              rows={5}
            />
          </label>

          <label>
            <span>PROJECT ID</span>
            <input
              value={loadingProjectId ? "Loading…" : projectId}
              readOnly
              disabled
              aria-readonly="true"
              className="new-project-readonly"
            />
          </label>

          <label>
            <span>WORKFLOW ENTRY POINT</span>
            <select
              value={brief.workflowEntryPoint}
              onChange={(event) =>
                updateBrief("workflowEntryPoint", event.target.value)
              }
              required
            >
              <option value={EMPTY_OPTION}>Select workflow…</option>
              {WORKFLOW_ENTRY_POINTS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>BUSINESS PROCESS</span>
            <select
              value={brief.businessProcess}
              onChange={(event) =>
                updateBrief("businessProcess", event.target.value)
              }
            >
              <option value={EMPTY_OPTION}>Optional</option>
              {BUSINESS_PROCESSES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>REQUESTER</span>
            <input
              value={brief.requester}
              onChange={(event) => updateBrief("requester", event.target.value)}
              placeholder="Name or email"
            />
          </label>

          <label>
            <span>DEPT</span>
            <input
              value={brief.dept}
              onChange={(event) => updateBrief("dept", event.target.value)}
              placeholder="Department"
            />
          </label>
        </div>

        <RequirementsEditor
          requirements={requirements}
          onChange={onRequirementsChange}
        />
      </section>

      <section
        className="new-project-panel new-project-offers"
        aria-labelledby="offers-heading"
      >
        <span className="new-project-step">STEP 2 · THE OFFERS</span>
        <h2 id="offers-heading">Upload vendor proposals</h2>
        <p className="new-project-panel-copy">
          PDF, DOCX and XLSX. Price tables are read cell by cell so each
          figure keeps its sheet and cell reference.
        </p>
        <div className="new-project-offers-body">
          <StagedFileDropzone
            files={files}
            onFilesChange={onFilesChange}
            heading="Drop files here"
            hint="or browse — 40 MB per file"
          />
        </div>
        {footer ? (
          <div className="new-project-offers-footer">{footer}</div>
        ) : null}
      </section>
    </div>
  );
}

export default ProjectBriefForm;
