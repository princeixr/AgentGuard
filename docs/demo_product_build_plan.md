# AgentGuard Demo Product Build Plan

Last updated: 2026-06-06

## Objective

Build a reliable demo-level AgentGuard product matching the four Stitch screens:

1. Live Interception
2. Trace Replay
3. Decision Memory
4. Risk & Operations

The demo must prove one complete product story:

```text
agent proposes a tool call
    -> AgentGuard intercepts before execution
    -> risk and evidence are shown in the UI
    -> an allow, block, or approval decision is enforced
    -> the session can be replayed and searched later
    -> aggregate risk appears in operations
```

The primary scripted scenario is **Draft vs Send**:

```text
User: "Summarize the latest budget thread and draft a reply. Do not send it."

gmail_search -> allow
gmail_read   -> allow
gmail_draft  -> allow
gmail_send   -> require approval or block
```

## Current State

### Ready to reuse

| Area | Current capability |
| --- | --- |
| Canonical contracts | `AgentGuardTraceV1`, features, scores, decisions, events, and session risk are implemented with Pydantic. |
| Governance | The deterministic firewall runs trace -> feature -> score -> decision -> session risk. |
| Runtime interception | Google ADK callbacks intercept proposed tool calls before execution. |
| Enforcement | Approval-required calls can be stopped before tool execution. |
| Persistence | Local JSONL/JSON persistence and Elastic indexing are implemented. |
| Retrieval | Elastic lexical retrieval maps historical decisions into risk features. |
| Historical data | OpenClaw traces and seed approved/blocked memory exist. |
| UI design | Four Stitch HTML screens and screenshots define the visual product. |

### Incomplete or inconsistent

| Area | Gap |
| --- | --- |
| Product frontend | Stitch files are static, independent HTML mockups with hard-coded data. |
| Dashboard backend | `src/agentguard/dashboard/app.py` is only a placeholder. |
| Read/query layer | Storage writes records but has no unified service for sessions, joined trace details, metrics, or local search. |
| Live updates | No SSE or WebSocket stream connects firewall events to the browser. |
| Approval workflow | ADK returns a synthetic blocked response; there is no pending approval state or operator action endpoint. |
| Demo data | Canonical JSONL outputs are not checked in as a complete, replayable demo dataset. |
| Script drift | `scripts/run_google_demo.py` references the removed `apps.google_adk_demo_agent` package. |
| Test environment | Core tests pass, but five ADK callback tests fail when `google-adk` is not installed. Current result: 31 passed, 5 failed. |
| Scoring quality | Formulas are deterministic placeholders and should be presented as demo policy scoring, not calibrated security probabilities. |

## Demo Scope

### Must have

- One shared application shell matching the Stitch navigation and design tokens.
- A deterministic local demo that does not require Gemini, Gmail OAuth, Docker, or Elastic.
- Optional real ADK and Elastic modes using the same API and UI contracts.
- Live event progression for the Draft vs Send scenario.
- A paused approval/block card with intent, proposed action, risk, rules, and precedents.
- Session replay with timeline, risk trajectory, and retrieved precedents.
- Decision memory table with search, filters, pagination, and details drawer.
- Risk dashboard with metrics derived from stored demo records.
- Clear runtime mode and health indicators so simulated and connected states are not confused.

### Defer

- Authentication, organizations, RBAC, billing, and multi-tenancy.
- General policy authoring UI; show policy references and allow threshold edits only if time permits.
- Production message queues and distributed event processing.
- Vector search, LLM-as-judge, and benchmark-calibrated scoring.
- Arbitrary agent onboarding and the inactive Sessions/Integrations pages.
- Real approval continuation inside an interrupted ADK execution. For the demo, approval can resolve the pending record and run a controlled mock executor.

## Recommended Architecture

```text
React dashboard SPA
        |
        | REST + Server-Sent Events
        v
FastAPI demo API
        |
        +-- Dashboard query service
        +-- Demo scenario runner
        +-- Approval service
        +-- AgentGuardFirewallV1
        |
        +-- Local JSONL repository (default)
        +-- Elastic repository (optional)
```

### Frontend

Create `apps/web/` with:

- **React + TypeScript + Vite** for a small, independently deployable dashboard SPA.
- **React Router** for the four product routes and trace/session deep links.
- **Tailwind CSS with CSS variables** for tokens translated from
  `agentguard_system/DESIGN.md`.
- **Radix UI primitives** for accessible dialogs, drawers, menus, tooltips, selects,
  and tabs without imposing a conflicting visual system.
- **TanStack Query** for REST server state, caching, invalidation, and degraded-mode
  retries.
- **TanStack Table** for Decision Memory filtering, sorting, pagination, and row
  selection.
- **Native `EventSource` wrapped in a small hook** for SSE. Keep live events out of a
  general-purpose global state store.
- **Apache ECharts** for risk trajectories, failure-mode distributions, and tool-risk
  charts. It handles dense operational data and responsive resizing better than
  hand-built SVG charts.
- **Zod** for runtime validation of API responses at the frontend boundary.
- **Vitest + React Testing Library + Playwright** for component, integration, and demo
  smoke tests.
- **Lucide React** for consistent technical iconography.

Do not ship four copied HTML files. Extract one shell and reusable components while preserving the Stitch visual hierarchy.

#### Why this stack

- The product is an authenticated-style operations console, not a content site. It does
  not need server rendering, SEO, React Server Components, or a second backend layer.
- FastAPI already owns API contracts, streaming, environment configuration, and service
  integration. Next.js or another full-stack frontend framework would duplicate those
  responsibilities.
- The Stitch output is already structured as Tailwind-oriented HTML, so React components
  can be extracted with minimal visual translation.
- TanStack Table is a better fit than a generic component-library table for the dense
  Decision Memory screen.
- Radix supplies behavior and accessibility while allowing the exact AgentGuard design
  system to remain in control.
- Native SSE is sufficient because the browser only receives ordered governance events;
  bidirectional WebSockets are unnecessary for the demo.

#### Avoid for this phase

- **Next.js**: useful when the frontend owns server rendering, auth middleware, or backend
  routes. None are required here.
- **Streamlit or Gradio**: fast for internal experiments but poorly matched to the
  supplied multi-pane product UI and interaction model.
- **Material UI or Ant Design**: their visual assumptions would require substantial
  overriding to match the Stitch design.
- **Redux**: the application state is mostly server state. TanStack Query plus local
  component state is enough.
- **WebSockets**: approval actions can use REST and event updates can use SSE.

#### Frontend structure

```text
apps/web/
    src/
        app/                 router, providers, application shell
        api/                 generated types, client, query keys, SSE client
        components/          shared AgentGuard design-system components
        features/
            live/
            replay/
            memory/
            operations/
        routes/
        styles/
            tokens.css
            globals.css
```

Generate TypeScript API types from FastAPI's OpenAPI schema during development. Zod
validation remains at important network boundaries, especially live-event payloads.

### Backend

Create `src/agentguard/api/` with FastAPI:

```text
app.py                 application factory and middleware
routes/live.py         event stream and pending interception
routes/sessions.py     session list and replay detail
routes/memory.py       joined trace/score/decision search
routes/operations.py   aggregate metrics and health
routes/demo.py         deterministic scenario controls
routes/approvals.py    approve, reject, and abort actions
services/query.py      joins canonical records into UI view models
services/demo_runner.py
services/approvals.py
repositories/local.py
repositories/elastic.py
models.py              API response/request contracts
```

FastAPI should depend on the existing AgentGuard models rather than introduce a second governance schema.

### Storage strategy

Use a repository interface with two implementations:

- `LocalDashboardRepository`: reads canonical JSONL and session-risk JSON. This is the default and must support the full demo.
- `ElasticDashboardRepository`: performs search and aggregations when Elastic is configured.

The frontend must receive the same response shapes in either mode. Elastic failure should degrade to local mode and update the health panel instead of breaking the demo.

## API Surface

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | API, storage, ADK, and Elastic status. |
| `GET` | `/api/v1/events/stream` | SSE stream of live events and decision updates. |
| `GET` | `/api/v1/interceptions/current` | Current paused or most recent interception. |
| `POST` | `/api/v1/demo/scenarios/{id}/start` | Start a deterministic scenario run. |
| `POST` | `/api/v1/demo/reset` | Restore checked-in demo fixtures. |
| `POST` | `/api/v1/approvals/{trace_id}` | Approve, reject, or abort a pending action. |
| `GET` | `/api/v1/sessions` | List sessions with decision and risk summaries. |
| `GET` | `/api/v1/sessions/{session_id}` | Joined replay timeline and risk trajectory. |
| `GET` | `/api/v1/memory` | Search/filter/paginate trace decision memory. |
| `GET` | `/api/v1/memory/{trace_id}` | Trace, features, score, decision, and evidence detail. |
| `GET` | `/api/v1/operations/summary` | Counts, rates, risky tools, failure modes, and health. |
| `GET` | `/api/v1/operations/export` | Download filtered decisions as JSONL or CSV. |

## Screen Implementation

### Live Interception

Data sources:

- `LiveEventV1` for the agent stream.
- `AgentGuardTraceV1` for intent, action, and arguments.
- `GuardScoreV1` for risk and dominant signals.
- `GuardDecisionV1` for verdict, explanation, policy rules, evidence, and latency.

Behavior:

- Start Demo runs the scripted scenario with short timed steps.
- SSE adds events without refreshing.
- The center panel changes to paused when approval is required.
- Approve, reject, and abort update the pending state and append an auditable event.
- Elastic evidence shows real retrieved traces when connected and checked-in precedents in local mode.

### Trace Replay

Build one ordered session view by joining records on `trace_id` and sorting by `step_index`.

Show:

- user input and each proposed/executed/blocked tool step,
- per-step and cumulative risk,
- intent versus attempted action,
- rules fired and dominant signals,
- similar precedents,
- final session outcome.

### Decision Memory

The list response should include:

- timestamp, agent, session, tool, final risk, decision, labels/signals, and trace ID.

Filters:

- free-text query,
- agent, tool, risk band, decision, and time range.

The details drawer should display the complete joined governance record. In local mode, implement bounded in-memory filtering over demo files; in Elastic mode, use `_search`.

### Risk & Operations

Compute metrics from decisions, scores, events, and session state:

- intercepted calls,
- intervention/block rate,
- p50/p95 decision latency,
- active/recent sessions,
- riskiest tools,
- dominant failure modes,
- component health.

Do not use the large hard-coded counts in the mockup. Demo metrics must reconcile with the underlying records.

## Delivery Phases

### Phase 0: Stabilize the demo baseline

Status: completed on 2026-06-06.

Estimated effort: 0.5-1 day.

- Fix or replace the stale `run_google_demo.py`.
- Make ADK-dependent tests skip cleanly when the optional package is absent, or install the locked environment.
- Add a single command that runs core tests without external services.
- Generate and check in a deterministic demo fixture containing at least:
  - one clean allow session,
  - one Draft vs Send approval/block session,
  - one file scope-creep block,
  - one prompt-injection block.
- Add a reset script that copies fixtures into a runtime data directory.

Acceptance:

- The same fixture produces the same traces, scores, and decisions on every run.
- The demo can start with no cloud credentials.

Implemented:

- deterministic fixtures under `demo/fixtures/v1/demo`,
- four sessions and 13 governed tool-call steps,
- fixture generation and runtime reset commands,
- repaired Google ADK demo entrypoint with dependency guidance,
- ADK callback tests skip only when `google-adk` is unavailable,
- verified baseline: 34 tests passed and 5 optional ADK callback tests skipped.

### Phase 1: Build the dashboard API

Status: completed on 2026-06-06.

Estimated effort: 1.5-2 days.

- Add FastAPI and the local repository.
- Implement joined view models and all read endpoints.
- Add scenario start/reset endpoints and SSE.
- Add API tests using temporary trace directories.
- Keep Elastic behind the repository interface.

Acceptance:

- OpenAPI documents all demo endpoints.
- API tests cover empty state, seeded state, filters, replay joins, and metrics.
- Starting a demo emits ordered events visible through SSE.

Implemented:

- FastAPI application and OpenAPI contract,
- local JSONL dashboard repository and joined query service,
- sessions, replay, memory, operations, health, scenario, and export endpoints,
- deterministic scenario runner, SSE broker, paused interception state, and operator
  resolution endpoints,
- verified through unit/API tests and real localhost HTTP requests.

### Phase 2: Build the shared frontend shell

Status: completed on 2026-06-06.

Estimated effort: 1 day.

- Scaffold `apps/web`.
- Translate the Stitch colors, typography, spacing, and navigation into Tailwind tokens.
- Add Radix primitives, TanStack Query/Table, the typed API client, and the SSE hook.
- Build the persistent sidebar/header and shared primitives.
- Add responsive behavior for laptop demo resolutions.

Acceptance:

- All four routes use one consistent shell.
- Static visual comparison is close to the supplied screenshots.

Implemented:

- React 19, TypeScript, Vite, Tailwind CSS, Radix, TanStack Query/Table, modular
  ECharts, Zod-ready API boundary, Vitest, and Lucide,
- shared navigation, page header, tokens, status badges, loading/error states, and
  route-level code splitting,
- clean npm dependency audit.

### Phase 3: Implement the core product story

Status: completed on 2026-06-06.

Estimated effort: 1.5-2 days.

- Implement Live Interception.
- Connect scenario controls and SSE.
- Implement paused decision details and approval actions.
- Implement Trace Replay for the completed session.

Acceptance:

- A presenter can run Draft vs Send from the UI.
- The send call is visibly intercepted before execution.
- The decision explanation and precedents are inspectable.
- The completed run immediately appears in Trace Replay.

Implemented:

- Live Interception route with SSE status, event progression, risk detail, precedents,
  and operator actions,
- Trace Replay route with session selection, ordered timeline, risk trajectory, and
  precedent cards,
- integrated Draft vs Send verification through the frontend proxy.

### Phase 4: Add memory and operations

Status: completed on 2026-06-06.

Estimated effort: 1-1.5 days.

- Implement Decision Memory list, filters, pagination, and drawer.
- Implement operations cards, charts, health, and export.
- Add loading, empty, degraded, and error states.

Acceptance:

- Every number and row is derived from stored records.
- Selecting a record links to its replay session.
- Local and Elastic modes use the same UI.

Implemented:

- Decision Memory search, tool/decision filters, TanStack table, and Radix detail drawer,
- Risk & Operations metrics, modular charts, component health, and CSV/JSONL export,
- metrics reconcile against the deterministic fixture.

### Phase 5: Connect optional real services and harden

Status: partially completed on 2026-06-06; cloud verification pending.

Estimated effort: 1-2 days.

- Verify real Google ADK callback interception.
- Verify Elastic queries and aggregations through the dashboard repository.
- Keep Gmail actions on a test account and approval enforcement enabled.
- Add a demo smoke test and a presenter startup command.
- Document fallback behavior and reset steps.

Acceptance:

- `make demo` or one equivalent command starts API and frontend.
- A cloud outage does not prevent the deterministic demo.
- Real mode is clearly labeled and can be enabled with environment variables.

Implemented:

- Elastic dashboard repository using the same query-service contract,
- startup selection of Elastic when enabled/configured with automatic local fallback,
- one-command `make demo`, combined `make test`, production frontend build, dependency
  audit, and local integrated smoke verification.

Requires environment verification:

- real Elastic Cloud dashboard reads with the configured account,
- real Google ADK callback execution with `google-adk` installed,
- optional Gmail MCP flow using a test account,
- manual browser visual comparison against the four Stitch screenshots.

## Testing Strategy

- Unit tests: repository joins, metric calculations, approval transitions, scenario runner.
- API tests: endpoint contracts, filters, pagination, SSE ordering, local/Elastic fallback.
- Frontend tests: status mapping, table filters, route rendering, approval actions.
- End-to-end smoke test: start fixture scenario, observe paused send, reject it, open replay, find it in memory.
- Manual visual pass against all four Stitch screenshots at 1440x900 and 1600x1000.

## Demo Definition of Done

The product is demo-ready when:

1. One command starts the web UI and API without cloud credentials.
2. The Draft vs Send scenario runs from the UI and pauses before `gmail_send`.
3. The UI shows the user intent, attempted action, risk components, rules, latency, and precedents.
4. An operator decision is recorded as an auditable event.
5. The session is immediately available in Trace Replay and Decision Memory.
6. Risk & Operations metrics reconcile with the stored demo records.
7. The demo survives missing Elastic, ADK, Gemini, Docker, and Gmail integrations.
8. Core and API tests pass in the documented environment.

## Recommended Build Order

The critical path is:

```text
deterministic fixtures
    -> local query repository
    -> FastAPI read/SSE endpoints
    -> shared React shell
    -> Live Interception
    -> Trace Replay
    -> Decision Memory
    -> Risk & Operations
    -> optional Elastic and real ADK
```

This order validates the product story early and prevents external integrations from
controlling demo reliability.
