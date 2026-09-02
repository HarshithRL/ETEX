import { useEffect, useState } from "react";
import { apiGet } from "../../../../../services/api";
import FileExplorer from "./components/FileExplorer";
import ChatPanel from "./components/ChatPanel";
import StudioPanel from "./components/StudioPanel";
import "./workspace-tab.css";

function WorkspaceTab({ projectId }) {
  const [data, setData] = useState(null);
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    setData(null);
    setMessages([]);
    setError(null);
    apiGet(`/api/procurement/projects/${projectId}/workspace`)
      .then((payload) => {
        setData(payload);
        setMessages(payload.chatMessages ?? []);
      })
      .catch(() => setError("Unable to load workspace."));
  }, [projectId]);

  if (!data && !error) {
    return <div className="workspace-tab">Loading…</div>;
  }

  if (error || !data) {
    return (
      <div className="workspace-tab">{error ?? "Workspace unavailable."}</div>
    );
  }

  return (
    <div className="workspace-tab">
      <FileExplorer files={data.files} storage={data.storage} />
      <ChatPanel
        projectId={projectId}
        messages={messages}
        userInitial={data.userInitial}
        onMessagesChange={setMessages}
      />
      <StudioPanel
        projectName={data.projectName}
        graph={data.graph}
      />
    </div>
  );
}

export default WorkspaceTab;
