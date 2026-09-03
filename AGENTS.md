# Mate — Agent & Skill Registry

> Cursor auto-loads this file. Canonical project handbook: [`agent.md`](agent.md). Build partner: say **hey buddy** / **buddy** / **dude** → [`.cursor/agents/buddy.md`](.cursor/agents/buddy.md).

---

## Session bootstrap (every new chat)

1. **Orient** — `graphify query "<task question>"` or skim `graphify-out/GRAPH_REPORT.md` god nodes.
2. **Context** — read [`agent.md`](agent.md) for stack, constraints, and gap roadmap.
3. **Route** — pick tool/skill/agent from the matrix below **before** grepping or bulk-reading files.
4. **Validate** — after React changes: `npx react-doctor@latest --verbose --scope changed` in `frontend/`.

**Exploration order:** graphify → targeted read/grep → implement → `--update` graph after large structural changes.

---

## Master routing matrix

| You need… | Use first | Then |
|-----------|-----------|------|
| Where code lives, cross-module flow, architecture | **graphify** `query` | grep/read files graph points to |
| Exact symbol, line proof, edge-case implementation | **grep** / **Read** | — |
| React pages, components, UX, a11y, visual quality | **react-expert** + **ia-react-frontend** SKILL.md | **javascript** / **typescript** by file type → **senior-frontend-developer** → **shadcn** → **react-doctor** |
| Flask routes, services, APIs, agent orchestration, persistence | **senior-backend-developer** subagent | graphify for flow context |
| LangChain / LangGraph / DeepAgents patterns & API | **LangChain MCP** (`docs-langchain` + `reference-langchain`) | read `agent_server/` |
| MLflow (tracing, eval, debug, metrics) | **mlflow-agent** → dispatches sub-skill | see MLflow table below |
| Databricks (CLI, deploy, data, serving) | **databricks-core** → product skill | see Databricks table below |
| shadcn/ui components (when adopted) | **shadcn** skill | `npx shadcn@latest add …` |
| Full-stack feature, gap analysis, ship increment | **buddy** subagent | delegates FE/BE skills above |
| React health / design audit | **react-doctor** | `/doctor` for full triage playbook |

---

## graphify (codebase map — use first)

| When | Command |
|------|---------|
| New session, architecture question, "how does X flow?" | `graphify query "<question>"` |
| Trace path between concepts | `graphify path "A" "B"` |
| After large refactors | `graphify . --update` |
| Visual exploration | open `graphify-out/graph.html` |

**Do not** grep-the-whole-repo cold. Graph is the map; grep is the magnifying glass.

---

## LangChain docs (MCP — configured in `.cursor/mcp.json`)

| Server | URL | Use for |
|--------|-----|---------|
| `docs-langchain` | `https://docs.langchain.com/mcp` | Concepts, how-tos, LangGraph tutorials, product guides |
| `reference-langchain` | `https://reference.langchain.com/mcp` | Class/method signatures, parameters, package API |

**Mate hotspots:** `agent_server/core/subagents/procure_agent/nodes/project_initiator.py` (`create_agent`), `agent_server/graph.py` (router), `procurement_chat.py` (workspace SSE + MCP prefetch), MCP stdio adapters.

**Index:** `https://docs.langchain.com/llms.txt`

---

## MLflow skills ([github.com/mlflow/skills](https://github.com/mlflow/skills))

Dispatch via **mlflow-agent** when intent is unclear. Mate roadmap item #7: MLflow tracing for agent observability.

| Skill | When to use |
|-------|-------------|
| **mlflow-onboarding** | First-time MLflow setup on Databricks |
| **instrumenting-with-mlflow-tracing** | Add tracing to LangChain/LangGraph/Flask agent paths; see `references/databricks.md` |
| **analyze-mlflow-trace** | Debug failed/wrong agent trace by span |
| **analyze-mlflow-chat-session** | Multi-turn workspace chat debugging |
| **retrieving-mlflow-traces** | Search/filter traces by session, user, time |
| **agent-evaluation** | End-to-end eval: datasets, scorers, runs |
| **build-a-scorer** | Design scorer suite for vendor-comparison quality |
| **querying-mlflow-metrics** | Token usage, latency, error-rate trends |
| **searching-mlflow-docs** | MLflow API/docs lookup |
| **fix-agent-issue** | Regression loop after agent fixes |

Install for team: `npx skills add mlflow/skills`

---

## Databricks skills (load `databricks-core` first)

Profile: `adb-7181820732839861`. Deploy target: **Databricks Apps** (Linux).

| Skill | Mate use case |
|-------|---------------|
| **databricks-core** | CLI, auth, profiles, catalog/table exploration, Genie Q&A |
| **databricks-apps** | **Deploy Mate** to Databricks Apps; app scaffolding |
| **databricks-app-design** | Data-app UX when building dashboard/KPI/chart surfaces on Databricks |
| **databricks-dabs** | Asset bundles (`databricks.yml`) for jobs, apps, pipelines |
| **databricks-lakebase** | Replace static mock data with Postgres persistence |
| **databricks-jobs** | Scheduled ingestion / batch jobs |
| **databricks-pipelines** | Lakeflow SDP for document/ETL pipelines |
| **databricks-model-serving** | Model endpoints, Foundation Model APIs |
| **databricks-vector-search** | RAG over parsed vendor documents |
| **databricks-serverless-migration** | Classic → serverless compute migration |

---

## Frontend agents & tools

On **any** frontend work, read the matching project skills **before** coding. Open `SKILL.md` first; load a `references/` file only for the topic at hand.

| Skill | Path | Use when |
|-------|------|----------|
| **react-expert** | `.cursor/skills/react-expert/` | React 19 components, hooks, state, performance |
| **ia-react-frontend** | `.cursor/skills/ia-react-frontend/` | Effects decision tree, component structure, RTL/Vitest |
| **javascript** | `.cursor/skills/javascript/` | `.js` / `.jsx` language, async, modules, JSDoc |
| **typescript** | `.cursor/skills/typescript/` | `.ts` / `.tsx`, tsconfig, type errors, TS performance |

**Mate stack wins** over Next.js App Router / RSC / Zustand examples in those packs unless the file already uses them. Stack: React 19, Vite 8, React Router 7, GSAP, `frontend/src/services/api.js`, shadcn (Nova) where `frontend/components.json` applies. Prefer existing `.jsx`/`.js`; do not convert to TypeScript unless asked.

### senior-frontend-developer (subagent)

**Invoke for:** React 19 + Vite SPA work, procurement UI, hub pages, GSAP motion, SSE chat UI, a11y, Web Vitals, design-quality review. **Read the skill packs above first.**

**Not for:** Flask/Python — use senior-backend-developer.

### react-doctor

```bash
cd frontend
npx react-doctor@latest --verbose --scope changed   # after edits
npx react-doctor@latest --verbose                   # full scan
npx react-doctor@latest design --verbose            # UI/a11y/motion audit
```

**`/doctor`** — fetch playbook: `https://www.react.doctor/prompts/react-doctor-agent.md`

### shadcn

Initialized in `frontend/` (`components.json`, Nova, Vite, lucide). Intake chat uses shadcn components. Follow **shadcn** skill: compose existing components, semantic tokens, FieldGroup forms. Pair with **senior-frontend-developer**.

---

## Backend agents & tools

### senior-backend-developer (subagent)

**Invoke for:** Flask blueprints, `services/`, SSE streaming, LangGraph orchestration, file upload endpoints, identity/auth, Databricks SDK integration, FastAPI agent wrapper (roadmap #8).

**Mate stack:** Flask 3, Python 3.11, type hints (`from __future__ import annotations`), thin routes + fat services.

**Not for:** React/CSS — use senior-frontend-developer.

---

## buddy (default build partner)

Say **hey buddy**, **buddy**, or **dude**. Owns end-to-end increments; delegates to FE/BE subagents and skills above. Reads `agent.md` + graphify first.

---

## Typical Mate workflows

| Goal | Route |
|------|-------|
| Wire document upload | graphify query → senior-backend-developer → parser in `agent_server/file_handler/parser/` |
| Vendor comparison UI | graphify query → react-expert + ia-react-frontend → senior-frontend-developer → react-doctor |
| Workspace chat bug | graphify query → analyze-mlflow-trace (when traced) or grep `procurement_chat.py` |
| Add MLflow tracing | mlflow-agent → instrumenting-with-mlflow-tracing |
| Deploy to Databricks Apps | databricks-core → databricks-apps + databricks-dabs |
| Replace mock data | databricks-core → databricks-lakebase + senior-backend-developer |
| LangGraph agent change | LangChain MCP + graphify query → senior-backend-developer |
| Linux import fix (case) | graphify query "App.jsx imports" → grep → fix |

---

## MCP servers (project)

See [`.cursor/mcp.json`](.cursor/mcp.json) — LangChain docs + reference preconfigured.

---

## graphify maintenance

```powershell
graphify . --update          # after code/doc changes
graphify hook install        # optional: rebuild graph on commit (when git initialized)
graphify agents install      # refresh graphify section in this file
```

Outputs: `graphify-out/graph.json`, `GRAPH_REPORT.md`, `graph.html`.
