# Tasks: AI PoC Planner

## Status Legend

- Priority: **Must**, **Should**, **Could**.
- Status: the specification baseline was approved on 2026-07-19; implementation tasks remain independently tracked below.
- Scope: XS = 1 file, S = 1–2 files, M = 3–5 files. Tasks larger than M must be split.

## Phase 0 — Specification Gate

### [Must] S0.1 Review and approve specification package

- [x] **Purpose:** Confirm product boundaries, architecture, scoring, hard gates, API and open questions before code. Approved by the user on 2026-07-19.
- **Modification scope:** `docs/spec/SPEC.md`, `docs/spec/PLAN.md`, `docs/spec/TASKS.md`, `PROJECT_LOG.md`.
- **Acceptance:** Human explicitly approves implementation or records required revisions; all open decisions needed by Task M1.1 are resolved or marked as implementation-safe TODOs.
- **Verification:** Manual review of cross-document consistency; no application source files exist.
- **Dependencies:** None.
- **Estimated scope:** S.

## Phase 1 — Foundation

### [Must] M1.1 Create executable Python scaffold and offline test entry

- [x] **Purpose:** Establish the smallest real project structure, dependency manifest and commands without implementing product behavior. Completed on 2026-07-19.
- **Modification scope:** `pyproject.toml`, `src/ai_poc_planner/`, `tests/`, README／AGENTS／SPEC command blocks, `PROJECT_LOG.md`.
- **Acceptance:** Standard `pip` editable install, `python -m pytest`, `python -m ruff check .` and `python -m ai_poc_planner` are grounded in real files and pass without runtime network or API keys.
- **Verification:** Run the four commands under Python 3.12; fake-provider tests prevent network use through the tested socket boundary.
- **Dependencies:** S0.1.
- **Estimated scope:** M.
- **Execution note:** The user explicitly expanded M1.1 to include initial contracts and a proposal-producing fake provider. M1.2 later completed full contract coverage; M1.4 remains open for embeddings and later Agent event seams.

### [Must] M1.2 Implement core Pydantic contracts

- [x] **Purpose:** Turn SPEC schema names and invariants into the shared contract layer. Completed on 2026-07-19.
- **Modification scope:** `domain/models.py`, `domain/enums.py`, `domain/workflow.py`, `domain/tools.py`, public exports, contract tests and synchronized project documentation.
- **Acceptance:** Persistence, workflow, Agent state and all six tool input/output contracts validate and JSON round-trip; missing dimensions, bad weights, invalid ranges, duplicate collections and invalid references are rejected. Per the approved M1.2 decision, calculation, gate precedence and recommendation decisions remain assigned to M1.3.
- **Verification:** `python -m pytest tests/domain/test_schemas.py` (80 tests) plus the complete offline suite.
- **Dependencies:** M1.1.
- **Estimated scope:** S.

### [Must] M1.3 Implement scoring rubric and hard-gate engine

- [x] **Purpose:** Create deterministic 1–5 scoring, 100% weighting and gate precedence independent of the Agent. Completed on 2026-07-19.
- **Modification scope:** scoring module, hard-gate rules/module, unit tests.
- **Acceptance:** Weights equal 100; all ratings enforce 1–5; `blocked > assistive_only > requires_controls > pass`; high ROI never overrides a gate.
- **Verification:** `python -m pytest tests/domain/test_scoring.py tests/domain/test_hard_gates.py tests/domain/test_assessment_engine.py` (119 M1.3 tests) plus the complete offline suite.
- **Dependencies:** M1.2.
- **Estimated scope:** M.

### [Must] M1.4 Define provider interfaces and deterministic fake model

- [x] **Purpose:** Make model and embeddings dependencies injectable before any real API integration. Completed on 2026-07-19.
- **Modification scope:** provider protocol module, fake model/embeddings module, tests.
- **Acceptance:** Fake responses are deterministic, support required tool/structured events and make no network call; domain code imports no provider SDK.
- **Verification:** `python -m pytest tests/providers/test_fake_provider.py` with network disabled, plus the complete offline suite.
- **Dependencies:** M1.2.
- **Estimated scope:** M.

### Checkpoint F1 — Foundation

- [x] All Phase 1 tests and lint pass.
- [x] Commands in README and AGENTS are executable and current.
- [x] User authorized the offline-only vertical-slice batch on 2026-07-19.

## Phase 2 — First Testable Vertical Slice

### [Must] M2.1 Create and load an analysis project

- [x] **Purpose:** Deliver the first end-to-end capability using SQLite: create and retrieve a project.
- **Modification scope:** project application service, SQLite project repository, migration/schema setup, tests.
- **Acceptance:** Project UUID/timestamps/status persist and reload from a temporary SQLite file; duplicate/invalid input has a stable error.
- **Verification:** `python -m pytest tests/integration/test_project_lifecycle.py`.
- **Dependencies:** M1.2.
- **Estimated scope:** M.
- **Completion note (2026-07-20):** SQLite `user_version = 1`, explicit connection lifecycle, project create/load, stable duplicate/not-found/input/corrupt-data errors and temporary-file integration tests are complete. The deterministic demo remains in memory by design.

### [Must] M2.2-lite Persist and continue a planning run

- [x] **Purpose:** Persist one natural-language planning run from initial clarification through the exact saved assessment, proposal and Markdown result.
- **Modification scope:** `PlanningRun` contract, SQLite v1→v2 migration, planning-run repository/service/coordinator, tests and synchronized scope documentation.
- **Acceptance:** A vague request saves one to four questions; one persisted answer batch can rerun to `completed`; loading by run ID returns the exact saved assessment, proposal and report; duplicate, invalid transition and corrupt storage paths use stable typed errors.
- **Verification:** `python -m pytest tests/integration/test_planning_run_lifecycle.py`.
- **Dependencies:** M1.4, M2.1.
- **Estimated scope:** M.
- **Scope adjustment (2026-07-20):** 展示版优先完成自然语言需求、追问、正式评估、结果保存、FastAPI 与 Streamlit 的完整闭环，暂缓完整 conversation resume。Full interview turns, arbitrary resume, checkpoints, Agent-state history and complete replay move to Roadmap without deleting their original contracts.
- **Completion note (2026-07-20):** `PlanningRun`, SQLite schema v2 and v1→v2 upgrade, create/get/update/list repository, lifecycle service and deterministic clarification→completed coordinator are complete. Thirty new tests cover contracts, migration, round trips, corruption, rollback and the persisted offline loop; the CLI demo remains in memory.

### [Must] M2.3-lite Add a common AI implementation pattern catalog

- [ ] **Purpose:** Give the later planning surface a small, reviewed directory of common AI delivery patterns.
- **Modification scope:** First slice: catalog domain contracts, fixed Python fixture, public catalog API, contract tests and synchronized documentation. Later slices own matching and deployment posture rules.
- **Acceptance:** `get_opportunity_catalog()` returns exactly the nine approved AI opportunities; non-AI alternatives remain separate; Grade E references are supplemental only; contracts contain no score, recommendation or hard-gate disposition.
- **Verification:** `python -m pytest tests/domain/test_opportunity_catalog.py`, then full offline suite and Ruff checks.
- **Dependencies:** M2.2-lite.
- **Estimated scope:** M.

### Roadmap History — Full Conversation and Separate Result Repositories

The original M2.2 interview-turn/session replay, arbitrary resume and conversation
checkpoint scope remains Roadmap work. The original M2.3–M2.5 separate assessment,
proposal and report repository tasks below remain historical design detail; the
demonstration does not wait for those additional repository boundaries because
M2.2-lite stores the validated final result on `PlanningRun`.

### [Roadmap] M2.3 Execute deterministic assessment and hard gates

- [ ] **Purpose:** Produce all six ratings, ROI/KPI assumptions, scope and independent gate disposition from completed interview data.
- **Modification scope:** assessment service, tool adapters, assessment repository, tests.
- **Acceptance:** Same input gives same outputs; missing critical data prevents final proposal; high-impact test case returns the expected gate regardless of score.
- **Verification:** `python -m pytest tests/integration/test_assessment_service.py`.
- **Dependencies:** M1.3, M2.2.
- **Estimated scope:** M.
- **Offline batch note:** the in-memory six-tool → M1.3 assessment path and error mapping are implemented; the assessment repository and persisted interview dependency remain open.

### [Roadmap] M2.4 Assemble and validate the structured PoC proposal

- [ ] **Purpose:** Convert persisted interview and assessment results into `PocProposal` with the fake model.
- **Modification scope:** proposal assembler, Agent workflow/state, proposal repository, tests.
- **Acceptance:** Proposal passes schema, contains each dimension once, records gate effects and stores no invalid output after bounded failure.
- **Verification:** `python -m pytest tests/integration/test_proposal_generation.py`.
- **Dependencies:** M2.3.
- **Estimated scope:** M.
- **Offline batch note:** deterministic proposal assembly covers pass, blocked, assistive-only and requires-controls outcomes; Agent workflow and proposal persistence remain open.

### [Roadmap] M2.5 Export a deterministic Markdown report

- [ ] **Purpose:** Complete the vertical slice with a readable, stable report artifact.
- **Modification scope:** Markdown renderer, export service/repository, golden-file tests.
- **Acceptance:** Report includes inputs, assumptions, cases, score table, hard gates, architecture, ROI/KPI, scope and next actions; section order is stable.
- **Verification:** `python -m pytest tests/domain/test_markdown_report.py tests/integration/test_vertical_slice.py`.
- **Dependencies:** M2.4.
- **Estimated scope:** M.
- **Offline batch note:** the typed fixed-order renderer, local file writer and CLI demo are implemented; the formal persisted vertical-slice dependency remains open.

### Checkpoint V1 — Core Vertical Slice

- [ ] Fake-model flow completes `建立專案 → 訪談 → 評估 → 報告` without network.
- [ ] Process/repository reload returns the persisted planning-run clarification or completed result.
- [ ] One normal case and one blocked case pass end to end.
- [ ] Human reviews the generated Markdown before retrieval work.

## Phase 3 — Local Case Knowledge Base

### [Must] M3.1 Add reviewed synthetic case format and fixtures

- [ ] **Purpose:** Establish public-safe evidence cases without private or copyrighted datasets.
- **Modification scope:** case schema/loader, 3–5 initial Markdown fixtures, tests.
- **Acceptance:** Only approved UTF-8 cases load; required front matter and content hash validate; source fields are inspectable.
- **Verification:** `python -m pytest tests/cases/test_case_loader.py`.
- **Dependencies:** M1.2.
- **Estimated scope:** M.

### [Must] M3.2 Build FAISS index with SQLite metadata mapping

- [ ] **Purpose:** Implement local embeddings storage and reliable metadata linkage.
- **Modification scope:** case metadata repository, FAISS index adapter, reindex service, tests.
- **Acceptance:** Fake embeddings produce stable top-k results; content-hash mismatch reports stale index; metadata is not treated as authoritative inside FAISS.
- **Verification:** `python -m pytest tests/infrastructure/test_case_index.py`.
- **Dependencies:** M1.4, M3.1.
- **Estimated scope:** M.

### [Must] M3.3 Integrate similar-case evidence into proposal

- [ ] **Purpose:** Add retrieval to the vertical slice without weakening deterministic gates.
- **Modification scope:** retrieval tool, Agent/application orchestration, proposal tests.
- **Acceptance:** Proposal includes case ID, source reference and fit summary; missing index fails explicitly; hard gates still run.
- **Verification:** `python -m pytest tests/integration/test_retrieval_proposal.py`.
- **Dependencies:** M2.4, M3.2.
- **Estimated scope:** M.

### Checkpoint K1 — Evidence-backed Proposal

- [ ] Retrieval metrics pass on reviewed fixtures.
- [ ] No unapproved case is indexed.
- [ ] Full fake-model vertical slice remains green.

## Phase 4 — API and UI

### [Must] M4.1 Expose the vertical slice through FastAPI

- [ ] **Purpose:** Implement the SPEC endpoints over existing application services.
- **Modification scope:** FastAPI composition/routes, error mapping, API tests.
- **Acceptance:** Required status codes and Pydantic response models match SPEC; errors have safe envelopes and correlation IDs.
- **Verification:** `python -m pytest tests/api`.
- **Dependencies:** M2.5, M3.3.
- **Estimated scope:** M.

### [Must] M4.2 Build basic Streamlit interview and report UI

- [ ] **Purpose:** Provide the public demo surface for project creation, interview, assessment and report display/export.
- **Modification scope:** Streamlit entry/client/views, smoke/manual checklist.
- **Acceptance:** User completes the standard flow; validation errors are visible; reload uses API/SQLite state rather than browser-only state.
- **Verification:** Streamlit smoke test plus documented manual flow in fake mode.
- **Dependencies:** M4.1.
- **Estimated scope:** M.

### Checkpoint U1 — Local Product Flow

- [ ] API and UI complete the same fake-mode vertical slice.
- [ ] Keyboard and error-summary manual checks pass.
- [ ] README screenshots/video are deferred until behavior is accepted.

## Phase 5 — Provider and Evaluation

### [Should] S5.1 Implement configured OpenAI-compatible adapters

- [ ] **Purpose:** Connect real chat and embedding endpoints without changing domain/application code.
- **Modification scope:** settings, chat adapter, embeddings adapter, opt-in tests.
- **Acceptance:** Model/provider/base URL/key are environment-driven; capability checks fail safely; tests skip without credentials.
- **Verification:** Fake suite plus explicit provider integration marker.
- **Dependencies:** M1.4, M3.2, M4.1.
- **Estimated scope:** M.

### [Should] S5.2 Add trajectory and multi-turn baseline suite

- [ ] **Purpose:** Validate tool selection and hard-gate coverage across the 15 research scenarios.
- **Modification scope:** baseline fixtures, trajectory evaluator, parametrized tests.
- **Acceptance:** Hard-gate miss rate is 0%; proposal schema validity is 100%; expected mandatory tools are called.
- **Verification:** `python -m pytest tests/evaluation`.
- **Dependencies:** M3.3.
- **Estimated scope:** M.

### [Could] C5.3 Add optional LangSmith export/evaluation

- [ ] **Purpose:** Compare real-model experiments without making LangSmith a runtime dependency.
- **Modification scope:** optional dependency/config, dataset export, documentation/tests.
- **Acceptance:** Feature is disabled by default; no sensitive fixture is uploaded; local pytest remains sufficient.
- **Verification:** Dry-run export test and opt-in manual experiment.
- **Dependencies:** S5.2.
- **Estimated scope:** M.

## Phase 6 — Docker and Publication Readiness

### [Must] M6.1 Add development and production-oriented Docker configuration

- [ ] **Purpose:** Package API/UI while preserving local SQLite/FAISS data and secret boundaries.
- **Modification scope:** Dockerfile, `compose.yaml`, `compose.dev.yaml`, Docker smoke test/docs.
- **Acceptance:** API keys come from environment; no real secret or DB password is committed; no database port exists; development ports bind to localhost.
- **Verification:** Build and run fake-mode vertical slice with Compose.
- **Dependencies:** M4.2.
- **Estimated scope:** M.

### [Must] M6.2 Finalize public README, project log and repository audit

- [ ] **Purpose:** Make the repository understandable and safe before any publish request.
- **Modification scope:** README, PROJECT_LOG, TASKS statuses, optional public assets.
- **Acceptance:** Commands are current; limitations and MIT license are visible; secret/local-artifact scan is clean; no remote/push occurs without separate authorization.
- **Verification:** Git status/diff review, ignored-file check and documented demo steps.
- **Dependencies:** All Must implementation tasks.
- **Estimated scope:** M.

## First Recommended Implementation Task

After human approval, execute **M1.1 — Create executable Python scaffold and offline test entry**. It creates the real command surface needed to verify every later vertical slice while adding no product behavior prematurely.
