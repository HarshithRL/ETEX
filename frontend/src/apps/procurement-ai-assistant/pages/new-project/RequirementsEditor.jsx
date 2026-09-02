function nextRef(rows) {
  return `REQ-${String(rows.length + 1).padStart(2, "0")}`;
}

function RequirementsEditor({ requirements, onChange }) {
  function updateRequirement(id, field, value) {
    onChange(
      requirements.map((row) =>
        row.id === id ? { ...row, [field]: value } : row,
      ),
    );
  }

  function addRequirement() {
    onChange([
      ...requirements,
      {
        id: `row-${requirements.length + 1}-${Date.now()}`,
        ref: nextRef(requirements),
        text: "",
        weight: "",
      },
    ]);
  }

  function removeRequirement(id) {
    if (requirements.length === 1) {
      return;
    }
    onChange(requirements.filter((row) => row.id !== id));
  }

  return (
    <div className="new-project-requirements">
      <div className="new-project-req-head">
        <span>REQUIREMENTS</span>
        <button
          className="primary-button new-project-add-line"
          type="button"
          onClick={addRequirement}
        >
          Add line
        </button>
      </div>

      <div
        className="new-project-req-row new-project-req-labels"
        aria-hidden="true"
      >
        <span>REF</span>
        <span>REQUIREMENT</span>
        <span>WT</span>
        <span />
      </div>

      {requirements.map((row) => (
        <div className="new-project-req-row" key={row.id}>
          <input
            aria-label="Requirement reference"
            value={row.ref}
            onChange={(event) =>
              updateRequirement(row.id, "ref", event.target.value)
            }
          />
          <input
            aria-label="Requirement"
            value={row.text}
            onChange={(event) =>
              updateRequirement(row.id, "text", event.target.value)
            }
            placeholder="Must-have capability or constraint"
          />
          <input
            aria-label="Weight"
            value={row.weight}
            onChange={(event) =>
              updateRequirement(row.id, "weight", event.target.value)
            }
            placeholder="20"
            inputMode="numeric"
          />
          <button
            className="new-project-remove"
            type="button"
            aria-label={`Remove ${row.ref}`}
            onClick={() => removeRequirement(row.id)}
            disabled={requirements.length === 1}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

export default RequirementsEditor;
