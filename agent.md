# Mate — Project Handbook

> **Note:** Cursor auto-loads `AGENTS.md` (skill registry + routing). This file is the canonical project handbook. The `buddy` subagent (`.cursor/agents/buddy.md`) reads it on every invocation. Say **hey buddy**, **buddy**, or **dude** to invoke buddy directly.

---

## North Star

present form

react + flask api

**final goal**:

**Hub page** is main page:

first focus is:

**Procurement Agent**

Business usecase: **vendor comparision** (user inputs the files outputs comparision matrics, PPT, project space AI assisstent)

react + other fornt end addording to requirement + flask api + langchain, langgraph + deegaphnts + dtabricks + mlflow + fast api (agent wrapper)

---

## What Mate Is

**Mate** is Etex's internal AI accelerator — a hub-and-spoke platform where each vertical (Procurement, Document Builder, etc.) is a self-contained React app backed by a shared Flask API and LangGraph agent stack on Databricks.

| Layer | Tech | Port / Host |
|-------|------|-------------|
| Frontend | React 19, Vite 8, React Router 7, GSAP | `http://localhost:5173` |
| API | Flask 3, flask-cors | `http://127.0.0.1:5000` |
| Agent | LangChain `create_agent` → LangGraph subgraphs | FastAPI `:8000` + Flask workspace SSE |
| LLM | `ChatDatabricks` via `model_factory.get_llm()` | `system.ai.claude-sonnet-5` |
| Identity | Databricks SDK `WorkspaceClient` | profile `adb-7181820732839861` |
| Deploy target | Databricks Apps (Linux/Ubuntu 22.04, Python 3.11) | — |

---

## Repository Layout

```
ai_application/
├── agent.md                  ← this handbook
├── requirements.txt          ← hand-maintained; do NOT compile on Windows (pywin32 pins)
├── frontend/                 ← React hub + vertical apps
│   └── src/
│       ├── pages/hub/        ← platform landing page
│       ├── apps/
│       │   └── procurement-ai-assistant/   ← only built vertical
│       └── services/api.js   ← apiGet / apiPost / apiPostSse
├── backend/                  ← Flask API (run from this directory)
│   ├── app.py                ← entry point, blueprint registration
│   ├── routes/               ← one blueprint per page/feature
│   └── services/             ← business logic, static payloads, chat orchestration
└── agent_server/             ← LangGraph agent, MCP, document parser
    ├── graph.py              ← parent router (route=new_project → procure_ai)
    ├── start_server.py       ← FastAPI SSE wrapper (:8000)
    ├── core/
    │   ├── model_factory/    ← ChatDatabricks / WorkspaceClient
    │   ├── state.py          ← MateAgentState (shared parent + subgraph)
    │   ├── context/prompts/  ← markdown system prompts
    │   └── subagents/procure_agent/  ← procure_ai graph + Project Initiator
    ├── mcp/                  ← FastMCP stdio servers
    └── file_handler/parser/  ← docling → native fallback (CLI included, not wired to API)
```

### Per-directory responsibilities

| Path | Owns |
|------|------|
| `frontend/src/pages/hub/` | Hub landing page — tool cards, welcome greeting |
| `frontend/src/apps/procurement-ai-assistant/` | Dashboard, projects list, project detail (overview / workspace / documents tabs) |
| `backend/routes/hub.py` | Hub page JSON payload |
| `backend/routes/procurement.py` | Procurement REST + SSE chat endpoints |
| `backend/routes/auth.py` | Session identity resolution |
| `backend/services/procurement_data.py` | **All static mock data** — projects, KPIs, files, graph coordinates |
| `backend/services/procurement_chat.py` | Workspace chat: MCP prefetch → `create_agent` + `get_llm()` → SSE |
| `backend/services/identity.py` | Dual identity (app SP + OBO user) for Databricks Apps vs local CLI |
| `agent_server/graph.py` | Parent LangGraph router (`route=new_project` → `procure_ai`) |
| `agent_server/start_server.py` | FastAPI wrapper: `POST /agent/stream` SSE |
| `agent_server/core/model_factory/` | `get_llm()` — ChatDatabricks via AI Gateway |
| `agent_server/core/subagents/procure_agent/` | procure_ai subgraph; Project Initiator `create_agent` node |
| `agent_server/core/context/prompts/proj_initiator.md` | Intake specialist system prompt |
| `agent_server/core/mcp_tools.py` | Load MCP tools via `langchain-mcp-adapters` stdio |
| `agent_server/mcp/project_context_server.py` | MCP tools: `get_project_context`, `list_workspace_files` |
| `agent_server/file_handler/parser/` | Document parsing (PDF/DOCX/XLSX/PPTX → Markdown) |

---

## Run Commands

### Prerequisites

```powershell
# Databricks profile (already the hardcoded default in model_factory and identity.py)
$env:DATABRICKS_CONFIG_PROFILE = "adb-7181820732839861"

# Python venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend deps
cd frontend
npm install
```

### Start dev servers

**One command (3 terminals):**

```powershell
.\start-dev.ps1
```

**Stop all dev servers (ports 5000, 5173, 8000):**

```powershell
.\stop-dev.ps1
```

Or manually:

```powershell
# Terminal 1 — Flask API (must run from backend/)
cd backend
python app.py          # → http://127.0.0.1:5000

# Terminal 2 — React frontend
cd frontend
npm run dev            # → http://localhost:5173

# Terminal 3 — Agent FastAPI (from repo root)
python -m agent_server.start_server    # → http://127.0.0.1:8000
```

Flask CORS is pinned to Vite on `5173` and also allows `5175` for a second local Vite. The agent FastAPI allows those origins plus other localhost Vite ports (preflight uses explicit headers — wildcard headers + credentials is a 400 in Starlette).

### Agent smoke test

```powershell
python -m agent_server.graph
```

### Document parser CLI

```powershell
python -m agent_server.file_handler.parser <file-or-dir> --out ./parsed/
```

---

## Request / Data Flow

### Hub → Procurement app

```
Browser (5173)
  → GET /api/hub                    → hub.jsx renders tool cards
  → click "Procurement AI Assistant"
  → /app/procurement-ai-assistant/dashboard
  → GET /api/procurement/dashboard  → static KPIs from procurement_data.py
```

### New-project intake chat

```
NewProjectChat.jsx
  → follow-up cards (name + workflow, then business process) and/or composer
  → POST /api/procurement/projects  { projectId, answered fields }
      missing fields stored as "untitled"
  → navigate /projects/:uuid?tab=workspace
  → ChatPanel workspace SSE; agent JSON draft → PATCH project metadata
```

Create only requires the existing project code (`GET /api/procurement/projects/next-code`). Name, workflow, and business process are collected on cards but are not required to open the workspace.

### Workspace chat (SSE)

```
ChatPanel.jsx
  → apiPostSse("/api/procurement/projects/<id>/workspace/chat/stream", { message, history })
  → procurement.py → procurement_chat.iter_workspace_chat_events()
      1. load_mcp_tools_for_project(project_id)     # stdio MCP server
      2. prefetch MCP tool results (ainvoke each tool)
      3. inject MCP output into system prompt
      4. create_agent(model=get_llm(), tools=[], system_prompt=...)   # tools NOT bound
      5. agent.astream(stream_mode="messages")
  → SSE frames back to browser
```

### SSE event contract

| Event | Payload | When |
|-------|---------|------|
| `context` | `{ label, detail }` | Workspace only: MCP tool loaded or failed |
| `updates` | `{ node }` | Intake: graph node started |
| `thought` | `{ text }` | Intake: reasoning content blocks (if Gateway emits them) |
| `token` | `{ text }` | Streaming LLM token chunk |
| `usage` | `{ input_tokens, output_tokens, total_tokens }` | Intake: model usage_metadata |
| `draft` | `{ name, workflowEntryPoint, … }` | Intake leftover / workspace: parsed JSON trailer applied via PATCH |
| `done` | `{ role: "ai", text, usage?, draft? }` | Final assembled reply |
| `error` | `{ detail }` | Validation or agent failure |

### Auth flow

```
GET /api/auth
  → auth.py → identity.resolve_identities(request)
      local:  WorkspaceClient(profile=DATABRICKS_CONFIG_PROFILE) → CLI user
      app:    WorkspaceClient() SP + x-forwarded-access-token OBO user
  → cached in Flask session["identity"]
```

---

## MCP Prefetch Constraint

**This is the single biggest architectural constraint on expanding the agent.**

Databricks AI Gateway for `system.ai.*` models currently rejects `tool_result` round-trips. Therefore:

1. MCP tools are loaded via `langchain-mcp-adapters` (stdio transport).
2. Each tool is called once via `ainvoke({})` before the agent runs.
3. Results are injected into the system prompt as a `## MCP project context` block.
4. `create_agent(..., tools=[])` — no tools are bound to the agent.

**Where to revisit:** when Gateway supports tool calling for `system.ai.*`, switch to binding tools directly on `create_agent` and remove the prefetch/inject pattern in `procurement_chat.py`.

---

## Conventions

- **Graphify first, grep second** — on every session, use `graphify query "<question>"` (see `graphify-out/`) to orient before grepping or bulk file reads. Grep is for deep dives after the graph narrows scope.
- **Blueprints per page/feature** — `routes/<name>.py` registers a `<name>_bp` blueprint.
- **Services for logic** — routes are thin; `services/` holds data and orchestration.
- **Static payloads server-side** — frontend fetches JSON from Flask; no client-side mocks.
- **New verticals** mirror `frontend/src/apps/procurement-ai-assistant/` structure (routes, pages, components).
- **New agent capability** goes in `agent_server/`, exposed through a Flask blueprint + service.
- **Type hints** — `from __future__ import annotations` in all Python modules.
- **Linting** — ruff (see `requirements.txt`).
- **No comments-as-narration** — code should be self-explanatory; comments only for non-obvious intent.
- **requirements.txt** — hand-maintained; never run `uv pip compile` on Windows (pins `pywin32`).

---

## Logging

Central logging lives in [`shared/logger_global/`](shared/logger_global/). **Only** [`shared/logger_global/controller.py`](shared/logger_global/controller.py) configures loguru sinks.

### Python

```python
from shared.logger_global import get_logger, bind_context

log = get_logger(__name__)
bind_context(project_id="proj-1", workflow="chat.prepare")
log.info("step complete duration_ms={}", 42)
```

- Agent modules: `get_logger(__name__, service="agent_server")`
- Never call `logger.add()` / `logger.remove()` outside `controller.py`
- Workflow names use dot notation: `chat.prepare`, `chat.mcp_prefetch`, `chat.stream`, `chat.done`, `chat.error`

### Environment variables

| Variable | Default (dev) | Purpose |
|----------|---------------|---------|
| `MATE_LOG_LEVEL` | `DEBUG` | Minimum log level |
| `MATE_LOG_FORMAT` | `pretty` | `pretty` or `json` |
| `MATE_LOG_DIR` | `logs/` | Rotating log files |
| `MATE_SERVICE` | set per entrypoint | `backend` / `agent_server` |
| `MATE_ENV` | `dev` | `prod` disables diagnose |
| `MATE_STDLIB_LOG_LEVEL` | `WARNING` | uvicorn/langchain/httpx via intercept |

Log files: `logs/{service}.log` and `logs/{service}.error.log` (gitignored).

### Frontend

Mirrored logger: [`frontend/src/shared/logger-global/`](frontend/src/shared/logger-global/).

```javascript
import { createLogger } from "../shared/logger-global/index.js";
const log = createLogger("pages.hub");
log.error("Failed to load", { context: { error: String(err) } });
```

`warn` and `error` in production POST to `POST /api/logs` (batched). API responses expose `X-Request-Id` for cross-layer tracing.

---

## Current State vs. Complete Business

| Capability | Status | Notes |
|------------|--------|-------|
| Hub page | Done | Tool cards, welcome greeting, theme toggle |
| Procurement dashboard | Mock | Static KPIs, project status, spend charts |
| Projects list + detail | Mock | 6 sample projects, tabs (overview/workspace/documents) |
| Workspace chat (SSE) | Working | MCP prefetch + Claude Sonnet via AI Gateway |
| MCP project context | Working | `get_project_context`, `list_workspace_files` |
| Document parser | Built, unwired | CLI works; no upload endpoint |
| File upload | Not started | — |
| Vendor comparison matrix | Not started | Core business use case |
| PPT generation | Not started | — |
| Knowledge graph (real) | Not started | UI shows static SVG coordinates |
| Deep agents | Not started | Listed in requirements.txt |
| MLflow tracing | Not started | Listed in requirements.txt |
| FastAPI agent wrapper | Working | `python -m agent_server.start_server` → `:8000` |
| New-project intake chat | Working | `/projects/new/chat` → procure_ai Project Initiator |
| Data persistence | Not started | All data is static Python dicts |
| Other hub tools | Placeholder | Document Builder, Translator, Scope Builder, Accounting |
| Databricks Apps deploy | Not started | requirements.txt targets Linux 3.11 |

---

## Known Issues

1. **Case-sensitive import mismatch** — `App.jsx` imports `./pages/hub/Hub` but file is `hub.jsx`. Same for `Dashboard`/`dashboard.jsx` and `Projects`/`projects.jsx`. Works on Windows, **breaks on Linux** (Databricks Apps build).
2. **Empty CSS** — `project-workspace.css` is 0 bytes.
3. **Mock-only data** — `procurement_data.py` has no database, no file storage, no real vendor documents.
4. **No git repo** — project is not yet version-controlled.

---

## Databricks Configuration

| Setting | Value |
|---------|-------|
| Profile | `adb-7181820732839861` |
| Host | `https://adb-7181820732839861.1.azuredatabricks.net` |
| Model | `system.ai.claude-sonnet-5` |
| Gateway path | `/ai-gateway/mlflow/v1/chat/completions` |
| Env var | `$env:DATABRICKS_CONFIG_PROFILE = "adb-7181820732839861"` |

The profile is hardcoded as `DEFAULT_PROFILE` in both `agent_server/core/model_factory/factory.py` and `backend/services/identity.py`. The env var only matters when overriding.

---

## Codebase Knowledge Graph

A graphify knowledge graph of this codebase lives in `graphify-out/`:

- `graph.html` — interactive browser visualization
- `GRAPH_REPORT.md` — audit report with communities, god nodes, surprising connections
- `graph.json` — raw graph data for programmatic queries

Query it: `graphify query "How does workspace chat flow work?"`

**Exploration order:** graphify query → targeted read/grep → implement. Re-run `graphify . --update` after large structural changes.

---

## Agent & skill registry

Full routing matrix (MLflow, Databricks, LangChain MCP, react-expert / ia-react-frontend / javascript / typescript, react-doctor, shadcn, FE/BE subagents): **[`AGENTS.md`](AGENTS.md)**.
