export const WORKFLOW_ENTRY_POINTS = [
  "Sourcing",
  "Vendor Comparison",
  "Contract Negotiation",
];

export const BUSINESS_PROCESSES = ["Indirect", "Direct"];

export const EMPTY_BRIEF = {
  name: "",
  workflowEntryPoint: "",
  businessProcess: "",
  requester: "",
  dept: "",
  targetSpend: "",
  category: "",
  awardHorizon: "",
  region: "",
  description: "",
};

export const EMPTY_REQUIREMENTS = [
  { id: "row-1", ref: "REQ-01", text: "", weight: "" },
];

function matchOption(value, options, aliases = []) {
  const raw = String(value || "").trim();
  if (!raw) {
    return "";
  }
  const lower = raw.toLowerCase();
  for (const option of options) {
    if (option.toLowerCase() === lower) {
      return option;
    }
  }
  for (const [needle, option] of aliases) {
    if (lower.includes(needle)) {
      return option;
    }
  }
  return "";
}

export function matchWorkflowEntryPoint(value) {
  return matchOption(value, WORKFLOW_ENTRY_POINTS, [
    ["compar", "Vendor Comparison"],
    ["negoti", "Contract Negotiation"],
    ["contract", "Contract Negotiation"],
    ["sourc", "Sourcing"],
  ]);
}

export function matchBusinessProcess(value) {
  return matchOption(value, BUSINESS_PROCESSES);
}

function asText(value) {
  return String(value || "").trim();
}

export function mergeBriefFromDraft(brief, draft) {
  if (!draft) {
    return brief;
  }
  const next = { ...brief };
  const name = asText(draft.name);
  const workflow = matchWorkflowEntryPoint(
    draft.workflowEntryPoint || draft.workflowPhase || draft.workflow,
  );
  const process = matchBusinessProcess(draft.businessProcess);
  const description = asText(draft.description) || asText(draft.brief);

  const mapped = {
    name,
    workflowEntryPoint: workflow,
    businessProcess: process,
    requester: asText(draft.requester),
    dept: asText(draft.dept),
    targetSpend: asText(draft.targetSpend),
    category: asText(draft.category),
    awardHorizon: asText(draft.awardHorizon),
    region: asText(draft.region),
    description,
  };

  for (const [field, value] of Object.entries(mapped)) {
    if (value) {
      next[field] = value;
    }
  }
  return next;
}

export function mergeRequirementsFromDraft(requirements, draft) {
  const incoming = draft?.requirements;
  if (!Array.isArray(incoming) || incoming.length === 0) {
    return requirements;
  }

  const rows = incoming.flatMap((item, index) => {
    if (typeof item === "string") {
      const text = item.trim();
      return text
        ? [
            {
              id: `draft-${index}`,
              ref: `REQ-${String(index + 1).padStart(2, "0")}`,
              text,
              weight: "",
            },
          ]
        : [];
    }
    if (!item || typeof item !== "object") {
      return [];
    }
    const text = asText(item.text) || asText(item.requirement);
    if (!text && !asText(item.ref)) {
      return [];
    }
    return [
      {
        id: asText(item.id) || `draft-${index}`,
        ref: asText(item.ref) || `REQ-${String(index + 1).padStart(2, "0")}`,
        text,
        weight: asText(item.weight),
      },
    ];
  });

  return rows.length > 0 ? rows : requirements;
}

export function canCreateProject({
  brief,
  submitting,
  loadingProjectId,
}) {
  return (
    Boolean(brief?.name?.trim()) &&
    Boolean(brief?.workflowEntryPoint?.trim()) &&
    !submitting &&
    !loadingProjectId
  );
}

export function createProjectPayload(projectId, brief, requirements) {
  return {
    ...(projectId?.trim() ? { projectId: projectId.trim() } : {}),
    name: brief.name.trim(),
    workflowEntryPoint: brief.workflowEntryPoint,
    businessProcess: brief.businessProcess || undefined,
    requester: brief.requester,
    dept: brief.dept,
    targetSpend: brief.targetSpend,
    category: brief.category,
    awardHorizon: brief.awardHorizon,
    region: brief.region,
    description: brief.description,
    requirements: requirements.map((row) => ({
      ref: row.ref,
      text: row.text,
      weight: row.weight,
    })),
  };
}
