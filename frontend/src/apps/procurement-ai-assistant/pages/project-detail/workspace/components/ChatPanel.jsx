import { useReducer } from "react";
import { apiPostSse } from "../../../../../../services/api";

const CENTER_TABS = [
  "Chat",
  "Document",
  "Spreadsheet",
  "Presentation",
  "Preview",
];

const initialChatUi = {
  tab: "Chat",
  draft: "",
  sending: false,
  sendError: null,
  streamText: "",
  contextEvents: [],
};

function chatUiReducer(state, action) {
  switch (action.type) {
    case "set_tab":
      return { ...state, tab: action.tab };
    case "set_draft":
      return { ...state, draft: action.draft };
    case "send_start":
      return {
        ...state,
        draft: "",
        sendError: null,
        sending: true,
        streamText: "",
        contextEvents: [],
      };
    case "token":
      return { ...state, streamText: action.text };
    case "context":
      return {
        ...state,
        contextEvents: [
          ...state.contextEvents,
          { label: action.label, detail: action.detail },
        ],
      };
    case "send_error":
      return { ...state, sendError: action.error, sending: false };
    case "send_done":
      return {
        ...state,
        sending: false,
        streamText: "",
        contextEvents: [],
      };
    default:
      return state;
  }
}

function messageKey(msg, index) {
  const prefix = msg.role === "user" ? "u" : "a";
  const snippet = (msg.text || "").slice(0, 48);
  return `${prefix}-${index}-${snippet}`;
}

function ChatPanel({ projectId, messages, userInitial, onMessagesChange }) {
  const [ui, dispatch] = useReducer(chatUiReducer, initialChatUi);

  async function handleSend(event) {
    event.preventDefault();
    const text = ui.draft.trim();
    if (!text || ui.sending || !projectId) {
      return;
    }

    const history = messages ?? [];
    const nextMessages = [...history, { role: "user", text }];
    onMessagesChange?.(nextMessages);
    dispatch({ type: "send_start" });

    let assembled = "";
    let failed = false;

    try {
      await apiPostSse(
        `/api/procurement/projects/${projectId}/workspace/chat/stream`,
        { message: text, history },
        (evt) => {
          if (evt.type === "token" && evt.text) {
            assembled += evt.text;
            dispatch({ type: "token", text: assembled });
          } else if (evt.type === "context") {
            dispatch({
              type: "context",
              label: evt.label || "Context",
              detail: evt.detail || "",
            });
          } else if (evt.type === "done") {
            assembled = evt.text || assembled;
            dispatch({ type: "token", text: assembled });
          } else if (evt.type === "error") {
            failed = true;
            dispatch({
              type: "send_error",
              error: evt.detail || "Agent stream failed.",
            });
          }
        },
      );

      if (!failed) {
        onMessagesChange?.([
          ...nextMessages,
          { role: "ai", text: assembled || "No reply." },
        ]);
        dispatch({ type: "send_done" });
      }
    } catch (err) {
      dispatch({
        type: "send_error",
        error: err?.message || "Unable to reach the agent.",
      });
    }
  }

  return (
    <section className="ws-chat">
      <div className="ws-center-tabs">
        {CENTER_TABS.map((name) => (
          <button
            key={name}
            type="button"
            className={ui.tab === name ? "active" : ""}
            onClick={() => dispatch({ type: "set_tab", tab: name })}
          >
            {name}
          </button>
        ))}
      </div>

      {ui.tab === "Chat" ? (
        <div className="ws-chat-content">
          {(messages ?? []).map((msg, index) =>
            msg.role === "user" ? (
              <div key={messageKey(msg, index)} className="ws-chat-user">
                <div className="ws-avatar">{userInitial}</div>
                <div className="ws-chat-bubble">{msg.text}</div>
              </div>
            ) : (
              <div key={messageKey(msg, index)} className="ws-chat-ai">
                <div className="ws-ai-avatar">AI</div>
                <div className="ws-chat-ai-body">
                  <strong>Procurement AI Agent</strong>
                  <p>{msg.text}</p>
                  {msg.points && (
                    <ul>
                      {msg.points.map((point) => (
                        <li key={point}>{point}</li>
                      ))}
                    </ul>
                  )}
                  {msg.sources && (
                    <div className="ws-sources">
                      {msg.sources.map((source) => (
                        <span key={source}>{source}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ),
          )}

          {ui.sending && (
            <div className="ws-chat-ai">
              <div className="ws-ai-avatar">AI</div>
              <div className="ws-chat-ai-body">
                <strong>Procurement AI Agent</strong>
                {ui.contextEvents.length > 0 && (
                  <div className="ws-stream-context" aria-live="polite">
                    {ui.contextEvents.map((ctx) => (
                      <div
                        key={`${ctx.label}::${ctx.detail}`}
                        className="ws-stream-context-item"
                      >
                        <span className="ws-stream-context-label">{ctx.label}</span>
                        {ctx.detail ? (
                          <span className="ws-stream-context-detail">{ctx.detail}</span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
                <p className="ws-stream-text">
                  {ui.streamText || "Thinking…"}
                  {ui.streamText ? (
                    <span className="ws-stream-caret" aria-hidden="true" />
                  ) : null}
                </p>
              </div>
            </div>
          )}

          <form className="ws-chat-composer" onSubmit={handleSend}>
            <label className="ws-chat-input-label" htmlFor="ws-chat-input">
              Message
            </label>
            <input
              id="ws-chat-input"
              type="text"
              placeholder="Ask about this project…"
              value={ui.draft}
              onChange={(e) =>
                dispatch({ type: "set_draft", draft: e.target.value })
              }
              disabled={ui.sending}
              autoComplete="off"
              aria-label="Ask about this project"
            />
            <button
              type="submit"
              className="primary-button"
              disabled={ui.sending || !ui.draft.trim()}
            >
              Send
            </button>
          </form>
          {ui.sendError && (
            <p className="ws-chat-error" role="alert">
              {ui.sendError}
            </p>
          )}
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
