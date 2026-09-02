import { useMemo, useReducer, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { BrainIcon, MessageSquareIcon, SendIcon } from "lucide-react";

import { AGENT_BASE, apiPostSse } from "../../../../services/api";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

import NewProjectChrome from "./NewProjectChrome";
import ProjectBriefForm from "./ProjectBriefForm";
import { createProject } from "./createProject";
import { OPENER, initialStream, intakeThreadId, streamReducer } from "./intakeChat";
import { NEW_PROJECT_FORM_PATH, NEW_PROJECT_PATH } from "./paths";
import {
  EMPTY_BRIEF,
  EMPTY_REQUIREMENTS,
  canCreateProject,
  createProjectPayload,
  mergeBriefFromDraft,
  mergeRequirementsFromDraft,
} from "./projectFormOptions";
import { useNextProjectCode } from "./useNextProjectCode";
import "./NewProject.css";
import "./NewProjectForm.css";
import "./NewProjectChat.css";

gsap.registerPlugin(useGSAP);

function newThoughtId() {
  return crypto.randomUUID();
}

const FALLBACK_REPLY = "I could not generate a reply. Please try again.";

function parseSseText(evt) {
  if (typeof evt?.text === "string" && evt.text.length > 0) {
    return evt.text;
  }
  if (typeof evt?.raw === "string" && evt.raw.length > 0) {
    try {
      const parsed = JSON.parse(evt.raw);
      if (typeof parsed?.text === "string") {
        return parsed.text;
      }
    } catch {
      /* ignore */
    }
  }
  return "";
}

function ThoughtPanel({ thoughts }) {
  if (thoughts.length === 0) {
    return null;
  }
  return (
    <Collapsible defaultOpen>
      <CollapsibleTrigger render={<Button variant="ghost" size="sm" />}>
        <BrainIcon data-icon="inline-start" />
        Reasoning
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="flex flex-col gap-2 rounded-lg bg-muted p-3">
          {thoughts.map((item) => (
            <p key={item.id} className="text-muted-foreground text-xs">
              {item.text}
            </p>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function IntakeMessages({ messages, sending, streamText, thinking }) {
  if (messages.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <MessageSquareIcon />
          </EmptyMedia>
          <EmptyTitle>No messages yet</EmptyTitle>
          <EmptyDescription>
            Share a project name and workflow phase to start filling the form.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <ol className="flex flex-col gap-4 pr-3">
      {messages.map((msg) => (
        <li
          key={msg.id}
          data-intake-msg={msg.id}
          className={cn(
            "flex gap-3",
            msg.role === "user" ? "flex-row-reverse" : "flex-row",
          )}
        >
          <Avatar size="sm">
            <AvatarFallback>{msg.role === "ai" ? "AI" : "You"}</AvatarFallback>
          </Avatar>
          <div
            className={cn(
              "max-w-[85%] rounded-lg px-3 py-2",
              msg.role === "ai" ? "bg-muted" : "bg-primary text-primary-foreground",
            )}
          >
            <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
          </div>
        </li>
      ))}
      {sending ? (
        <li data-intake-msg="streaming" className="flex gap-3">
          <Avatar size="sm">
            <AvatarFallback>AI</AvatarFallback>
          </Avatar>
          <div className="max-w-[85%] rounded-lg bg-muted px-3 py-2">
            {streamText ? (
              <p className="text-sm whitespace-pre-wrap">{streamText}</p>
            ) : thinking ? (
              <p className="text-muted-foreground text-sm">Thinking…</p>
            ) : (
              <div className="flex flex-col gap-2">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="h-3 w-64" />
              </div>
            )}
          </div>
        </li>
      ) : null}
    </ol>
  );
}

function absorbDraft(draft, setBrief, setRequirements) {
  if (!draft) {
    return;
  }
  setBrief((current) => mergeBriefFromDraft(current, draft));
  setRequirements((current) => mergeRequirementsFromDraft(current, draft));
}

function NewProjectChat() {
  const navigate = useNavigate();
  const containerRef = useRef(null);
  const composerRef = useRef(null);
  const tokenBadgeRef = useRef(null);
  const seenMsgs = useRef(null);
  if (seenMsgs.current === null) {
    seenMsgs.current = new Set(["opener"]);
  }
  const threadId = useMemo(() => intakeThreadId(), []);
  const { projectId, loadingProjectId, loadError } = useNextProjectCode();

  const [composer, setComposer] = useState("");
  const [files, setFiles] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [brief, setBrief] = useState(EMPTY_BRIEF);
  const [requirements, setRequirements] = useState(EMPTY_REQUIREMENTS);
  const [messages, setMessages] = useState([
    { id: "opener", role: "ai", text: OPENER },
  ]);
  const [stream, dispatch] = useReducer(streamReducer, initialStream);

  const canCreate = canCreateProject({
    projectId,
    brief,
    submitting,
    loadingProjectId,
  });
  const formError = error || loadError;

  useGSAP(
    () => {
      const root = containerRef.current;
      if (!root) {
        return;
      }
      if (!stream.sending) {
        seenMsgs.current.delete("streaming");
      }
      const nodes = root.querySelectorAll("[data-intake-msg]");
      nodes.forEach((el) => {
        const id = el.getAttribute("data-intake-msg");
        if (!id || seenMsgs.current.has(id)) {
          return;
        }
        seenMsgs.current.add(id);
        gsap.fromTo(
          el,
          { opacity: 0, y: 12 },
          { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" },
        );
      });
    },
    { scope: containerRef, dependencies: [messages.length, stream.sending] },
  );

  useGSAP(
    () => {
      const root = containerRef.current;
      if (!root) {
        return;
      }
      const viewport = root.querySelector("[data-slot='scroll-area-viewport']");
      const last = [...root.querySelectorAll("[data-intake-msg]")].at(-1);
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
        return;
      }
      last?.scrollIntoView({ block: "end", inline: "nearest" });
    },
    {
      scope: containerRef,
      dependencies: [messages.length, stream.sending, stream.streamText],
    },
  );

  useGSAP(
    () => {
      if (!tokenBadgeRef.current || !stream.usage?.total_tokens) {
        return;
      }
      gsap.fromTo(
        tokenBadgeRef.current,
        { scale: 0.92 },
        { scale: 1, duration: 0.2, ease: "power2.out" },
      );
    },
    { dependencies: [stream.usage?.total_tokens], scope: containerRef },
  );

  function updateBrief(field, value) {
    setBrief((current) => ({ ...current, [field]: value }));
  }

  function focusComposer() {
    const node = composerRef.current || document.getElementById("intake-draft");
    node?.focus();
  }

  async function handleSend(event) {
    event.preventDefault();
    const text = composer.trim();
    if (!text || stream.sending) {
      return;
    }

    setComposer("");
    setMessages((current) => [
      ...current,
      { id: `u-${Date.now()}`, role: "user", text },
    ]);
    setError(null);
    dispatch({ type: "send_start" });
    focusComposer();

    let assembled = "";
    let pendingQuestion = "";
    let failed = false;

    try {
      await apiPostSse(
        "/agent/stream",
        {
          message: text,
          thread_id: threadId,
          route: "new_project",
        },
        (evt) => {
          if (evt.type === "token" && evt.text) {
            assembled = evt.replace ? evt.text : assembled + evt.text;
            dispatch({ type: "token", text: assembled });
          } else if (
            (evt.type === "reasoning" || evt.type === "thought") &&
            evt.text
          ) {
            dispatch({ type: "reasoning", id: newThoughtId(), text: evt.text });
          } else if (evt.type === "question") {
            const questionText = parseSseText(evt);
            if (questionText) {
              pendingQuestion = questionText;
              assembled = questionText;
              dispatch({ type: "question", text: questionText });
            }
          } else if (evt.type === "updates" && evt.node) {
            dispatch({ type: "updates", id: newThoughtId(), node: evt.node });
          } else if (evt.type === "usage") {
            dispatch({
              type: "usage",
              input_tokens: evt.input_tokens,
              output_tokens: evt.output_tokens,
              total_tokens: evt.total_tokens,
            });
          } else if (evt.type === "draft") {
            absorbDraft(evt, setBrief, setRequirements);
          } else if (evt.type === "done") {
            const doneText = parseSseText(evt);
            if (doneText && doneText !== FALLBACK_REPLY) {
              assembled = doneText;
            } else if (pendingQuestion) {
              assembled = pendingQuestion;
            } else if (doneText) {
              assembled = doneText;
            }
            dispatch({ type: "token", text: assembled });
            if (evt.draft) {
              absorbDraft(evt.draft, setBrief, setRequirements);
            }
            if (evt.usage) {
              dispatch({ type: "usage", ...evt.usage });
            }
          } else if (evt.type === "error") {
            failed = true;
            dispatch({
              type: "send_error",
              error: evt.detail || "Agent stream failed.",
            });
          }
        },
        { base: AGENT_BASE },
      );

      if (!failed) {
        const reply =
          (assembled && assembled !== FALLBACK_REPLY ? assembled : "") ||
          pendingQuestion ||
          assembled ||
          FALLBACK_REPLY;
        setMessages((current) => [
          ...current,
          { id: `a-${Date.now()}`, role: "ai", text: reply },
        ]);
        dispatch({ type: "send_done" });
      }
    } catch (err) {
      dispatch({
        type: "send_error",
        error: err?.message || "Unable to reach the agent.",
      });
    } finally {
      focusComposer();
    }
  }

  function onComposerKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    handleSend(event);
  }

  async function handleCreate() {
    if (!canCreate) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await createProject(
        createProjectPayload(projectId, brief, requirements),
        files,
      );
      navigate(created.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create project.");
      setSubmitting(false);
    }
  }

  const tokenTotal = stream.usage?.total_tokens ?? 0;

  return (
    <NewProjectChrome
      crumbs={[
        { label: "New project", to: NEW_PROJECT_PATH },
        { label: "Chat" },
      ]}
    >
      <header className="new-project-chat-header">
        <span className="new-project-eyebrow">CREATE A SOURCING PROJECT</span>
        <h1>Chat with the procurement agent</h1>
        <p>
          Tell the agent the project name and workflow phase. It fills the
          same brief and upload form as the manual path. Create when those
          two fields are set.
        </p>
      </header>

      <div className="intake-chat-layout">
        <div ref={containerRef} className="intake-chat-pane">
          <Card
            className="h-full min-h-0"
            role="region"
            aria-label="Intake chat"
          >
            <CardHeader className="shrink-0">
              <CardTitle>Describe the buy in chat</CardTitle>
              <CardDescription>
                Ask for a name and workflow phase first. Other fields fill as
                you talk.
              </CardDescription>
              <CardAction>
                <Tooltip>
                  <TooltipTrigger render={<Button variant="ghost" size="sm" />}>
                    <span ref={tokenBadgeRef}>
                      <Badge variant="secondary">
                        {tokenTotal ? `${tokenTotal} tokens` : "No usage yet"}
                      </Badge>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>
                    {stream.usage
                      ? `In ${stream.usage.input_tokens} · Out ${stream.usage.output_tokens}`
                      : "Token counts appear after the model replies."}
                  </TooltipContent>
                </Tooltip>
              </CardAction>
            </CardHeader>

            <CardContent className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
              <ThoughtPanel thoughts={stream.thoughts} />
              <ScrollArea className="min-h-0 flex-1">
                <IntakeMessages
                  messages={messages}
                  sending={stream.sending}
                  streamText={stream.streamText}
                  thinking={
                    stream.sending &&
                    !stream.streamText &&
                    stream.thoughts.length > 0
                  }
                />
              </ScrollArea>
            </CardContent>

            <CardFooter className="mt-auto shrink-0 flex-col items-stretch gap-2">
              <form className="flex flex-col gap-2" onSubmit={handleSend}>
                <InputGroup>
                  <InputGroupTextarea
                    ref={composerRef}
                    id="intake-draft"
                    aria-label="Message"
                    value={composer}
                    onChange={(event) => setComposer(event.target.value)}
                    onKeyDown={onComposerKeyDown}
                    placeholder="Project name and workflow phase…"
                    rows={3}
                  />
                  <InputGroupAddon align="block-end">
                    <InputGroupButton
                      type="submit"
                      variant="default"
                      disabled={stream.sending || !composer.trim()}
                    >
                      {stream.sending ? (
                        <Spinner data-icon="inline-start" />
                      ) : (
                        <SendIcon data-icon="inline-start" />
                      )}
                      Send
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
                {stream.sendError ? (
                  <p className="text-destructive text-sm" role="alert">
                    {stream.sendError}
                  </p>
                ) : null}
              </form>
            </CardFooter>
          </Card>
        </div>

        <div className="intake-chat-form">
          <ProjectBriefForm
            projectId={projectId}
            loadingProjectId={loadingProjectId}
            brief={brief}
            onUpdateBrief={updateBrief}
            requirements={requirements}
            onRequirementsChange={setRequirements}
            files={files}
            onFilesChange={setFiles}
            footer={
              <>
                {formError ? (
                  <p className="new-project-error">{formError}</p>
                ) : null}
                <button
                  className="primary-button new-project-create"
                  type="button"
                  disabled={!canCreate}
                  onClick={handleCreate}
                >
                  {submitting ? "Creating…" : "Create New Project"}
                </button>
                <p className="new-project-offers-hint">
                  Create stays disabled until project name and workflow phase
                  are set. You can still edit the form or upload files first.
                </p>
                <Link
                  className="intake-chat-form-switch"
                  to={NEW_PROJECT_FORM_PATH}
                >
                  Switch to manual form
                </Link>
              </>
            }
          />
        </div>
      </div>
    </NewProjectChrome>
  );
}

export default NewProjectChat;
