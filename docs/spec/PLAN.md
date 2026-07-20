# Implementation Plan: AI PoC Planner

## 1. Status

Version 1 was approved by the user on 2026-07-19 as the implementation baseline. Work remains gated by the task order in `TASKS.md`.

## 2. Overview

Implementation follows a contract-first, vertical-slice strategy. The first usable path is not “all database, then all API, then all UI”; it is one thin end-to-end workflow:

`建立專案 → 建立 planning run → 保存追問／补充 → 執行 deterministic 評估與 hard gates → 保存 Pydantic proposal／Markdown`

The fake model and local temporary storage are established before any real provider integration so tests remain reproducible.

## 3. Dependency Graph

```text
Pydantic contracts + scoring/hard-gate rules
├── SQLite repository interfaces and implementation
├── fake model + deterministic interview policy
├── assessment application service
│   ├── tool adapters
│   └── PocProposal assembler
├── Markdown renderer
└── FastAPI endpoints
    └── Streamlit UI

Case schema + SQLite metadata
└── embeddings adapter
    └── FAISS index
        └── retrieve_similar_cases tool

Provider adapter contract
├── fake model implementation
└── OpenAI-compatible implementation (after vertical slice)
```

## 4. Architecture Decisions

| Decision | Rationale | Consequence |
|---|---|---|
| Single LangChain Agent | MVP is an interview/planning workflow, not an autonomous multi-agent system | One state schema and bounded tool set |
| Domain rules outside prompt | Scores and gates must be deterministic, testable and auditable | Prompt cannot override domain outcomes |
| Pydantic as contract source | Shared validation for API, tools, state handoff and report | Schema changes require spec and contract-test updates |
| SQLite for all business state | Local-first, single-user MVP with minimal operations | Concurrency and multi-tenant concerns deferred |
| FAISS only for embeddings | Efficient local similarity search; metadata remains relational/auditable | Reindex process must preserve SQLite-to-vector mapping |
| Provider adapter | OpenAI-compatible default without provider lock-in | Capability checks and normalized errors required |
| Fake model first | Reproducible tests with no network or paid account | Real provider is not needed to validate the core product |
| FastAPI application service boundary | UI and API share use cases, not duplicated logic | Streamlit calls API or shared client, not repositories directly |
| Hard gates before score interpretation | High ROI cannot cancel prohibited or uncontrolled risk | Final recommendation can be capped or blocked independently |
| Two-file Compose strategy | Separate local port exposure from production-oriented base settings | No database port and no committed secrets |

## 5. Phased Implementation

### Phase 0 — Specification Approval

Inputs:

- `deep-research-report.md`
- `docs/spec/SPEC.md`
- this plan and `TASKS.md`

Outputs:

- Approved or revised contracts, weights, hard gates, API and open questions.

Checkpoint:

- Human explicitly approves entering implementation.

### Phase 1 — Foundation and Test Harness

Inputs:

- Approved schema and command decisions.

Work:

- Create `pyproject.toml`, minimal packages and pytest configuration.
- Implement Pydantic contracts, scoring and hard gates.
- Implement settings and fake-model/provider interfaces.
- Establish SQLite repositories using temporary test databases.

Outputs:

- Executable test command.
- Deterministic contract and rule tests.
- No UI or real provider yet.

Checkpoint:

- `python -m pytest` and `python -m ruff check .` pass offline.
- README and AGENTS commands are updated from planned to active.

### Phase 2 — First Vertical Slice

Inputs:

- Foundation contracts and fake model.

Execution note (2026-07-19): before SQLite work, an explicitly authorized
in-memory tracer slice now exercises fixed interview data, all six deterministic
tools, M1.3 assessment, proposal assembly, Markdown export and CLI output. This
does not replace the SQLite persistence/reload acceptance below; it proves the
application boundaries while database, API, UI, FAISS and Agent work remain deferred.

Scope adjustment (2026-07-20): the demonstration prioritizes a complete
natural-language request → clarification → formal result → persisted history
loop. Full interview-turn persistence, arbitrary resume, conversation checkpoints,
Agent-state history and complete replay move to the Roadmap. Existing contracts
remain documented and are not deleted.

Work in dependency order:

1. Create/read project.
2. Create a durable `PlanningRun` for one natural-language request.
3. Persist structured intent, gaps and one clarification-answer batch.
4. Run the existing deterministic offline workflow after required facts are present.
5. Persist and reload the exact assessment, proposal and Markdown result.
6. Add the reviewed common AI implementation-pattern catalog in the next lite task.
7. Expose the persisted slice through minimal FastAPI endpoints.
8. Present the same saved result through Streamlit.

Outputs:

- Automated vertical-slice test from project creation to report.
- Durable planning-run history after process/repository reload.

Checkpoint:

- Happy path and one blocked high-impact path pass without network.
- No invalid proposal is stored.

Execution note (2026-07-20): M2.2-lite now persists the clarification state and
exact final assessment／proposal／Markdown payload on `PlanningRun`. SQLite schema
v2 supports fresh initialization and the single v1→v2 upgrade while preserving
projects. Full conversation replay remains Roadmap work.

### Phase 3 — Local Case Retrieval

Inputs:

- Approved case format and working vertical slice.

Work:

- Add reviewed synthetic case fixtures.
- Persist metadata and content hashes in SQLite.
- Implement embeddings adapter and fake embeddings.
- Build/rebuild FAISS index with stale-index detection.
- Connect `retrieve_similar_cases` and evidence references to proposal.

Outputs:

- Deterministic retrieval tests and source-linked proposal evidence.

Checkpoint:

- Approved cases are indexed; unapproved cases are excluded.
- Missing/stale index fails explicitly.

### Phase 4 — FastAPI and Streamlit Product Surface

Inputs:

- Stable application services and API contracts.

Work:

- Complete API endpoints and safe error envelopes.
- Build basic Streamlit project/interview/proposal/report screens.
- Ensure Streamlit session is not the durable source of truth.
- Add manual accessibility and error-flow checks.

Outputs:

- Local end-to-end demonstration of the standard interview.

Checkpoint:

- Browser flow completes vertical slice using fake mode.
- Reload displays the saved planning-run clarification or completed result from SQLite.

### Phase 5 — Real Provider Adapter and Evaluation

Inputs:

- Passing fake-model flow.

Work:

- Implement the configured OpenAI-compatible model and embeddings adapters.
- Add capability checks for tool calling and structured output.
- Normalize timeout, refusal and schema errors.
- Run opt-in integration tests only when safe credentials are present.
- Optionally export baseline cases to LangSmith.

Outputs:

- Provider can be changed by configuration without domain changes.

Checkpoint:

- Fake suite remains default and fully passing.
- Provider integration tests skip safely when credentials are absent.

### Phase 6 — Docker and Public-release Readiness

Inputs:

- Stable API/UI commands and local persistence paths.

Work:

- Add Dockerfile, `compose.yaml` and `compose.dev.yaml`.
- Mount one local data volume; expose only application ports in dev.
- Confirm no secrets, database ports or generated data are committed.
- Update README, PROJECT_LOG and task statuses.

Outputs:

- Reproducible local Docker demo and publication checklist.

Checkpoint:

- Docker fake-mode vertical slice passes.
- Secret and tracked-file audit is clean.

## 6. Testing Strategy

| Level | Scope | Required before |
|---|---|---|
| Unit | Rubrics, weights, hard gates, ROI math, scope points, renderer | Phase 2 |
| Contract | Pydantic models and every tool input/output | Phase 2 |
| Repository | SQLite transactions, state snapshots, FAISS mapping | Phase 3 |
| Application integration | Use cases with fake model and temporary storage | Phase 2 |
| Trajectory | Required tool sequence, prohibited action absence | Phase 2 and 5 |
| Planning-run lifecycle | Gaps, one answer batch, completion and saved-result reload | Phase 2 |
| Roadmap multi-turn | Turns, arbitrary resume, checkpoints and replay | Roadmap |
| API | Status codes, response schemas and safe errors | Phase 4 |
| UI manual/smoke | Standard interview, validation, reload and export | Phase 4 |
| Docker smoke | Services, environment and persisted local volume | Phase 6 |
| Optional evaluation | LangSmith datasets/experiments | Phase 5 |

Testing rules:

- Default test invocation has no network.
- Real-provider tests use an explicit marker and skip without credentials.
- Every hard-gate rule has positive and negative cases.
- Weighted score tests recompute total independently and verify all weights sum to 100.
- Baseline cases include low-risk, missing-data, privacy-boundary and high-impact scenarios.

## 7. Key Risks and Alternatives

| Risk | Impact | Mitigation | Alternative |
|---|---|---|---|
| Model skips required tool | High | Deterministic application prechecks plus trajectory tests | Orchestrate mandatory tools outside model choice |
| Provider cannot combine tools and structured output | High | Capability check and `ToolStrategy`; bounded validation retry | Split tool phase and proposal assembly |
| Clarification loop repeats questions | Medium | One bounded question set and explicit run transitions | Return a stable failed／clarification result |
| High score masks unacceptable risk | High | Separate hard-gate engine with precedence tests | No score shown until gate completes |
| FAISS and SQLite metadata drift | High | Content hash, vector IDs and atomic reindex workflow | Disable retrieval until rebuild |
| Sensitive answers appear in logs | High | Structured safe logging and redaction tests | Log IDs and event types only |
| SQLite write contention | Low for MVP | Short transactions and one local writer assumption | Roadmap migration to PostgreSQL |
| Public cases contain private/copyrighted data | High | Synthetic cases, source review and approval flag | Keep only metadata templates |
| Five-day estimate proves unrealistic | Medium | Vertical slices and task checkpoints | Reduce first release to fake-mode CLI/API slice |

## 8. Parallelization and Sequencing

Must be sequential:

- Contracts → scoring/gates → application services → API/UI.
- Case metadata contract → FAISS mapping → retrieval tool.
- Fake provider → real provider.

Safe to parallelize after contracts stabilize:

- Markdown renderer and SQLite repository tests.
- Synthetic case writing and API error-contract tests.
- Streamlit presentation and Docker documentation after service contracts are fixed.

Any parallel work that changes shared Pydantic models must stop and coordinate through `SPEC.md` first.

## 9. Definition of Done

A task is done only when:

1. Its acceptance criteria are satisfied.
2. Relevant tests and lint pass.
3. No secret, database, FAISS index, report, trace or user data is tracked.
4. Contract changes are reflected in `SPEC.md`.
5. `TASKS.md` status is updated.
6. `PROJECT_LOG.md` is updated for meaningful changes.
7. README／AGENTS commands are updated if workflows changed.

The MVP is done only when all Must tasks pass, the fake-model vertical slice works through API and Streamlit, Markdown export is validated, Docker development mode works, and the human accepts the result.

## 10. Open Decisions Before Implementation

- Python 3.12 and standard `pip` commands are confirmed by M1.1.
- Confirm whether report content is stored in SQLite, file, or both.
- Confirm default real model and embeddings settings for documentation.
- Decide whether LangSmith is Should or Could for the first public release.
- Confirm whether bilingual output is deferred.
