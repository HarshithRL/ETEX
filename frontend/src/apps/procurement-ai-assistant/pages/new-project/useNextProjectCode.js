import { useEffect, useState } from "react";

import { fetchNextProjectCode } from "./createProject";

export function useNextProjectCode() {
  const [projectId, setProjectId] = useState("");
  const [loadingProjectId, setLoadingProjectId] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function loadProjectId() {
      setLoadingProjectId(true);
      try {
        const code = await fetchNextProjectCode();
        if (!cancelled) {
          setProjectId(code);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error ? err.message : "Unable to load project ID.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingProjectId(false);
        }
      }
    }
    loadProjectId();
    return () => {
      cancelled = true;
    };
  }, []);

  return { projectId, loadingProjectId, loadError };
}
