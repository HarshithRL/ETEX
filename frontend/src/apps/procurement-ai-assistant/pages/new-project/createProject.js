import { apiGet, apiPost, apiPostForm } from "../../../../services/api";
import { PROJECTS_LIST_PATH } from "./paths";

export async function fetchNextProjectCode() {
  const data = await apiGet("/api/procurement/projects/next-code");
  return data.projectId;
}

export async function createProject(payload, files = []) {
  const created = await apiPost("/api/procurement/projects", payload);

  if (files.length > 0) {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    await apiPostForm(`/api/procurement/projects/${created.id}/files`, formData);
  }

  return {
    id: created.id,
    name: created.name,
    projectId: created.projectId,
    href: `${PROJECTS_LIST_PATH}/${created.id}`,
  };
}
