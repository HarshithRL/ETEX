export const THREAD_KEY = "mate-intake-thread-id";

export const OPENER =
  "Let’s start a sourcing project. What should we call it, and which workflow phase are you in — Sourcing, Vendor Comparison, or Contract Negotiation? I’ll fill the form as we go.";

export const initialStream = {
  sending: false,
  streamText: "",
  thoughts: [],
  pendingQuestion: "",
  usage: null,
  sendError: null,
};

export function intakeThreadId() {
  if (typeof window === "undefined") {
    return "intake";
  }
  try {
    const existing = sessionStorage.getItem(THREAD_KEY);
    if (existing) {
      return existing;
    }
    const created = crypto.randomUUID();
    sessionStorage.setItem(THREAD_KEY, created);
    return created;
  } catch {
    return crypto.randomUUID();
  }
}

export function streamReducer(state, action) {
  switch (action.type) {
    case "send_start":
      return {
        ...initialStream,
        sending: true,
      };
    case "token":
      return { ...state, streamText: action.text };
    case "reasoning":
    case "thought":
      return {
        ...state,
        thoughts: [
          ...state.thoughts,
          { id: action.id, kind: "reasoning", text: action.text },
        ],
      };
    case "question":
      return {
        ...state,
        pendingQuestion: action.text,
        streamText: state.streamText || action.text,
      };
    case "updates":
      return {
        ...state,
        thoughts: [
          ...state.thoughts,
          { id: action.id, kind: "node", text: `Running ${action.node}` },
        ],
      };
    case "usage":
      return {
        ...state,
        usage: {
          input_tokens: action.input_tokens ?? state.usage?.input_tokens ?? 0,
          output_tokens: action.output_tokens ?? state.usage?.output_tokens ?? 0,
          total_tokens: action.total_tokens ?? state.usage?.total_tokens ?? 0,
        },
      };
    case "send_error":
      return { ...state, sendError: action.error, sending: false };
    case "send_done":
      return {
        ...state,
        sending: false,
        streamText: "",
        sendError: null,
        thoughts: [],
        pendingQuestion: "",
      };
    default:
      return state;
  }
}
