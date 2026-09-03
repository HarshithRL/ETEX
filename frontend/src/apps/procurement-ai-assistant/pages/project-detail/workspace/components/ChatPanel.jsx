import { MessageSquare } from "lucide-react";

import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";

import ChatAttachMenu from "./ChatAttachMenu";
import ChatMarkdown from "./ChatMarkdown";
import ChatThoughtProcess from "./ChatThoughtProcess";
import { useWorkspaceChatStream } from "./useWorkspaceChatStream";

const CENTER_TABS = [
  "Chat",
  "Document",
  "Spreadsheet",
  "Presentation",
  "Preview",
];

function messageKey(msg, index) {
  const prefix = msg.role === "user" ? "u" : "a";
  const snippet = (msg.text || "").slice(0, 48);
  return `${prefix}-${index}-${snippet}`;
}

function ChatAiBody({
  thoughts,
  text,
  streaming = false,
  durationMs = null,
  points,
  sources,
}) {
  return (
    <div className="ws-chat-ai-body" aria-live={streaming ? "polite" : undefined}>
      <ChatThoughtProcess
        thoughts={thoughts}
        live={streaming}
        durationMs={durationMs}
      />
      <ChatMarkdown text={text} streaming={streaming} />
      {points ? (
        <ul>
          {points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      ) : null}
      {sources ? (
        <div className="ws-sources">
          {sources.map((source) => (
            <span key={source}>{source}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function CenterTabs({ tab, onTab }) {
  return (
    <div className="ws-center-tabs">
      {CENTER_TABS.map((name) => (
        <button
          key={name}
          type="button"
          className={tab === name ? "active" : ""}
          onClick={() => onTab(name)}
        >
          {name}
        </button>
      ))}
    </div>
  );
}

function ChatComposer({
  draft,
  sending,
  uploading,
  onDraftChange,
  onSend,
  onAddFile,
}) {
  return (
    <form className="ws-chat-composer" onSubmit={onSend}>
      <ChatAttachMenu
        onAddFile={onAddFile}
        disabled={uploading || sending}
      />
      <label className="ws-chat-input-label" htmlFor="ws-chat-input">
        Message
      </label>
      <input
        id="ws-chat-input"
        type="text"
        placeholder="Ask about this project…"
        value={draft}
        onChange={(e) => onDraftChange(e.target.value)}
        disabled={sending}
        autoComplete="off"
        aria-label="Ask about this project"
      />
      <button
        type="submit"
        className="primary-button"
        disabled={sending || !draft.trim()}
      >
        Send
      </button>
    </form>
  );
}

function ChatPanel({
  projectId,
  messages,
  userInitial,
  pendingMessage = "",
  onPendingConsumed,
  onMessagesChange,
  onAddFile,
  uploading = false,
  uploadError = null,
  uploadStatus = null,
}) {
  const { ui, dispatch, sendMessage, bottomRef } = useWorkspaceChatStream({
    projectId,
    messages,
    pendingMessage,
    onPendingConsumed,
    onMessagesChange,
  });
  const sending = ui.status === "sending";
  const hasMessages = (messages ?? []).length > 0;

  async function handleSend(event) {
    event.preventDefault();
    await sendMessage(ui.draft.trim());
  }

  return (
    <section className="ws-chat">
      <CenterTabs
        tab={ui.tab}
        onTab={(name) => dispatch({ type: "set_tab", tab: name })}
      />

      {ui.tab === "Chat" ? (
        <div className="ws-chat-content">
          {!hasMessages && !sending ? (
            <Empty className="ws-chat-empty">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <MessageSquare />
                </EmptyMedia>
                <EmptyTitle>Ask about this project</EmptyTitle>
                <EmptyDescription>
                  Send a question to the procurement agent. Replies stream in
                  here.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : null}

          {(messages ?? []).map((msg, index) =>
            msg.role === "user" ? (
              <div key={messageKey(msg, index)} className="ws-chat-user">
                <div className="ws-avatar">{userInitial}</div>
                <div className="ws-chat-bubble">{msg.text}</div>
              </div>
            ) : (
              <div key={messageKey(msg, index)} className="ws-chat-ai">
                <div className="ws-ai-avatar">AI</div>
                <ChatAiBody
                  thoughts={msg.thoughts}
                  text={msg.text}
                  durationMs={msg.thoughtMs}
                  points={msg.points}
                  sources={msg.sources}
                />
              </div>
            ),
          )}

          {sending ? (
            <div className="ws-chat-ai">
              <div className="ws-ai-avatar">AI</div>
              <ChatAiBody
                thoughts={ui.thoughts}
                text={ui.streamText}
                streaming
              />
            </div>
          ) : null}

          <div ref={bottomRef} />

          <ChatComposer
            draft={ui.draft}
            sending={sending}
            uploading={uploading}
            onDraftChange={(draft) => dispatch({ type: "set_draft", draft })}
            onSend={handleSend}
            onAddFile={onAddFile}
          />
          {uploadStatus && !uploadError ? (
            <p className="ws-chat-upload-status" role="status">
              {uploadStatus}
            </p>
          ) : null}
          {uploadError ? (
            <p className="ws-chat-error" role="alert">
              {uploadError}
            </p>
          ) : null}
          {ui.sendError ? (
            <p className="ws-chat-error" role="alert">
              {ui.sendError}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="ws-center-placeholder">
          <p>{ui.tab} view will appear here.</p>
        </div>
      )}
    </section>
  );
}

export default ChatPanel;
