export const OPENER = "Let’s start a sourcing project.";

export const PROCESS_PROMPT = "Which business process is this buy?";

export function intakeSeedKey(projectUuid) {
  return `mate-intake-messages:${projectUuid}`;
}

export function writeIntakeSeed(projectUuid, payload) {
  try {
    sessionStorage.setItem(intakeSeedKey(projectUuid), JSON.stringify(payload));
  } catch {
    /* ignore quota / private mode */
  }
}

export function readIntakeSeed(projectUuid) {
  try {
    const raw = sessionStorage.getItem(intakeSeedKey(projectUuid));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function intakePendingSentKey(projectUuid) {
  return `mate-intake-pending-sent:${projectUuid}`;
}

export function markIntakePendingSent(projectUuid) {
  try {
    sessionStorage.setItem(intakePendingSentKey(projectUuid), "1");
  } catch {
    /* ignore */
  }
  clearIntakePending(projectUuid);
}

export function wasIntakePendingSent(projectUuid) {
  try {
    return sessionStorage.getItem(intakePendingSentKey(projectUuid)) === "1";
  } catch {
    return false;
  }
}
