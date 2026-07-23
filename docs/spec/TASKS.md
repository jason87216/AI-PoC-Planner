# Tasks: viable MVP reset

## Status legend

- **Must**: required before viable-MVP release.
- **Should**: valuable after the blocking path works.
- **Deferred**: explicitly outside this MVP.
- Every task is one small PR and must state tests plus a human verification.

## Deprecated roadmap items

The following previous completion logic is deprecated and must not be revived as
product acceptance:

- a fake-model API/Streamlit vertical slice as a successful MVP;
- scripted fixed-field clarification as a viable interview;
- fake-mode browser flow as evidence of real AI analysis;
- Docker, FAISS, or live-provider claims in the current product README.

Fake models remain permitted for deterministic automated tests only.

## Phase 0 — Specification reset

### [Must] S0.1 Approve viable-MVP specification package

- **Purpose:** Approve the real-provider-first product contract.
- **Scope:** Documentation only.
- **Acceptance:** SPEC, PLAN, TASKS, README, and project log agree that no
  formal analysis occurs without a real selected profile.
- **Verification:** Cross-document review and `git diff --check`.

## Phase 1 — Model profile and OpenAI-compatible connection

### [Must] P1.1 Define model profile and provider-status contracts

- **Purpose:** Define profile name, base URL, model name, optional API key,
  selected status, and safe connection-test result.
- **Scope:** Pydantic/API contracts and tests only.
- **Dependencies:** S0.1.
- **Acceptance:** No contract implies a fake fallback.

### [Must] P1.2 Add ignored local JSON model-profile repository

- **Purpose:** Persist profile CRUD and selection locally, including optional
  API key, without committing secrets.
- **Scope:** Local repository/config boundary and tests.
- **Dependencies:** P1.1.
- **Acceptance:** Create, edit, delete, and select profiles; ignored file is
  never staged.

### [Must] P1.3 Add OpenAI-compatible chat adapter

- **Purpose:** Send real chat requests through an injected adapter.
- **Scope:** Provider adapter and unit tests; no report/interview/UI rewrite.
- **Dependencies:** P1.1.
- **Acceptance:** Explicit timeout/safe error handling; no runtime fake default.

### [Must] P1.4 Add profile connection test and provider-status API

- **Purpose:** Test selected profile connectivity and expose safe current status.
- **Scope:** API/application boundary and tests.
- **Dependencies:** P1.2, P1.3.
- **Acceptance:** Absent/failed profile blocks formal analysis.

### [Must] P1.5 Add opt-in llama.cpp integration test

- **Purpose:** Verify a manually started llama.cpp OpenAI-compatible server.
- **Scope:** Explicit integration marker/test and documentation.
- **Dependencies:** P1.3, P1.4.
- **Acceptance:** Not run by default; validates empty API-key path when server
  permits it.

### Checkpoint P1

- Human verifies a real local endpoint is called and formal analysis is rejected
  when no tested profile is selected.

**Implementation/UAT status (PR #11):** Offline validation and real llama.cpp
UAT passed. P1.1 contracts, P1.2 local JSON profile repository, P1.3
OpenAI-compatible adapter, P1.4 safe profile/status API plus readiness guard,
and P1.5 opt-in llama.cpp test are implemented; profile CRUD, selection,
connection test, readiness, invalidation, and process-restart status reset
passed with no fake runtime fallback. Phase 2 and viable-MVP completion remain
pending.

## Phase 2 — Project versions, conversation, and facts

### [Must] P2.1 Define project/version/conversation/fact contracts

- **Purpose:** Model project identity, immutable versions, visible conversation,
  confirmed facts, assumptions, references, and correction state.
- **Dependencies:** P1.
- **Acceptance:** No system prompt, chain of thought, trajectory, or raw
  provider metadata appears in durable visible records.

### [Must] P2.2 Persist projects and immutable completed versions

- **Purpose:** Save history and create a new version for completed-project edits.
- **Dependencies:** P2.1.
- **Acceptance:** Reload is durable; completed versions cannot be overwritten.

### [Must] P2.3 Persist visible conversation and protect confirmed facts

- **Purpose:** Save user/AI messages and prevent silent overwrite of confirmed
  facts while allowing explicit corrections.
- **Dependencies:** P2.1, P2.2.
- **Acceptance:** Contradictions/missing facts are detectable and test-covered.

### Checkpoint P2

- Human reloads a project and creates a new version from a completed version.

## Phase 3 — AI understanding and interview

### [Must] P3.1 Add minimal initial-brief contract and API

- **Purpose:** Require project name, current workflow/problem, desired outcome,
  and available data; accept unknown/no data.
- **Dependencies:** P1, P2.
- **Acceptance:** Optional users/owner and known constraints only; no generic
  supplementary-notes field.

### [Must] P3.2 Add AI requirement-understanding confirmation

- **Purpose:** Obtain structured understanding and user confirmation/correction.
- **Dependencies:** P3.1.
- **Acceptance:** Unconfirmed claims remain assumptions.

### [Must] P3.3 Add bounded contextual interview

- **Purpose:** Enable at most three rounds of at most three questions, each with
  why, impact, and example.
- **Dependencies:** P3.2.
- **Acceptance:** User can answer unknown, add corrections, and the AI updates
  structured facts without storing reasoning traces.

### Checkpoint P3

- Human UAT with a real model confirms questions are contextual rather than a
  fixed template.

## Phase 4 — Analysis, rubric, and hard gates

### [Must] P4.1 Define AI option and evidence-backed rubric contracts

- **Purpose:** Add AI/non-AI/hybrid options, six ratings, fact references, gaps,
  risks, and score-improvement conditions.
- **Dependencies:** P3.
- **Acceptance:** Catalog-external candidate is marked `unstandardized_candidate`.

### [Must] P4.2 Validate AI ratings and calculate weighted total

- **Purpose:** Program validates score range/references and calculates totals.
- **Dependencies:** P4.1.
- **Acceptance:** No old fixed Boolean rules set a final rating.

### [Must] P4.3 Apply existing hard gates to AI analysis

- **Purpose:** Enforce safety/governance conflicts after AI proposal generation.
- **Dependencies:** P4.2.
- **Acceptance:** AI cannot bypass a triggered gate.

### Checkpoint P4

- Human verifies a real model can recommend non-AI, foundations-first, or hybrid.

## Phase 5 — Cases and report

### [Must] P5.1 Define and validate reviewed local success cases

- **Purpose:** Add manually curated source-backed case records and tag/rule
  filtering.
- **Dependencies:** P4.
- **Acceptance:** No FAISS and no fabricated company, metric, or source.

### [Must] P5.2 Assemble full Markdown planning report

- **Purpose:** Produce every section in the SPEC report contract.
- **Dependencies:** P4, P5.1.
- **Acceptance:** Report is business-actionable and preserves fact references.

### Checkpoint P5

- Business reviewer approves sample report usefulness, not merely schema validity.

## Phase 6 — Streamlit product UI

### [Must] P6.1 Build home/history and model-settings views

- **Purpose:** Show project history and profile management without developer
  controls.
- **Dependencies:** P1, P2.

### [Must] P6.2 Build brief, confirmation, and interview views

- **Purpose:** Render the Phase 3 flow through HTTP only.
- **Dependencies:** P3, P6.1.

### [Must] P6.3 Build analysis and readable report views

- **Purpose:** Render Phase 4–5 results and Markdown export without raw JSON,
  UUIDs, API URLs, or technical warnings.
- **Dependencies:** P4, P5, P6.2.

### Checkpoint P6

- Human completes a real-model planning flow without internal identifiers.

## Phase 7 — Local launcher

### [Must] P7.1 Add install batch entry point

- **Purpose:** Check Python 3.12, create venv, install dependencies, initialise
  local storage/data, and disable Streamlit email prompt/telemetry.
- **Dependencies:** P6.

### [Must] P7.2 Add start batch entry point

- **Purpose:** Start API, wait for health, start Streamlit, and open browser.
- **Dependencies:** P7.1.

### [Must] P7.3 Add reliable stop batch entry point

- **Purpose:** Stop the two owned local processes without broad process kills.
- **Dependencies:** P7.2.

## Phase 8 — Portfolio UAT

### [Must] P8.1 Execute viable-MVP acceptance review

- **Purpose:** Verify real provider, blocked-no-provider behavior, versioning,
  interview, analysis choices, report, launcher, and ignored-artifact hygiene.
- **Dependencies:** P1–P7.
- **Acceptance:** Human product UAT passes; fake-model test suite is supporting
  evidence only.

## Deferred

- Multi-agent, LangGraph, FAISS, Docker, cloud deployment, accounts, online
  search, multi-tenancy, production-grade credential encryption, PDF/DOCX, and
  automatic llama.cpp/model installation.
