# Tasks: viable MVP

## Status legend

- **Complete**: implemented and merged or accepted as the current baseline.
- **Next**: the next bounded implementation target.
- **Deferred**: intentionally outside the current MVP path.
- Each implementation task should remain one reviewable PR with automated tests and
  an explicit human-verification note.

## Product acceptance rules

The following are not valid product acceptance evidence:

- a fake-model API or Streamlit vertical slice;
- scripted fixed-field clarification presented as a viable interview;
- fake-provider browser output presented as real AI analysis;
- unsupported claims that Docker, FAISS, cloud deployment, or a provider integration
  are complete.

Fake providers remain permitted only for deterministic automated tests.

## Phase 0 — Specification reset

### S0.1 Approve viable-MVP specification package — Complete

- The product is real-provider-first.
- Formal analysis requires a selected, enabled, tested model profile.
- SPEC, PLAN, TASKS, README, and PROJECT_LOG must not imply a runtime fake fallback.

## Phase 1 — Model profiles and OpenAI-compatible connection

### P1.1–P1.5 — Complete

Delivered:

- model-profile and safe provider-status contracts;
- ignored local profile persistence with optional API keys;
- OpenAI-compatible chat adapter with bounded errors and timeouts;
- connection test, readiness guard, and provider-status API;
- opt-in llama.cpp integration test, including an empty-key local path.

Human and integration UAT verified real local inference and blocked-no-profile behavior.

## Phase 2 — Project versions, conversation, and facts

### P2.1–P2.3 — Complete

Delivered:

- project, immutable version, visible conversation, and fact contracts;
- additive SQLite persistence and completed-version protection;
- append-only confirmed-fact revisions, explicit corrections, and fact/message
  references without storing prompts, raw provider responses, or reasoning traces.

## Phase 3 — AI understanding and interview

### P3.1–P3.3 — Complete

Delivered:

- minimal initial brief;
- structured requirement understanding with confirmation and correction;
- bounded contextual interview of at most three rounds and three questions per round;
- durable reload and unknown/missing fact handling.

Real-model UAT verified contextual questions rather than a fixed template.

## Phase 4 — Analysis, rubric, and hard gates

### P4.1–P4.3 — Complete

Delivered:

- AI, non-AI, hybrid, and foundations-first option contracts;
- evidence-backed six-dimension ratings and program-owned weighted totals;
- deterministic HG-01 through HG-07 evaluation that provider output cannot bypass;
- conservative treatment of unknown critical inputs.

The provider proposes structured options and narrative; program code owns formal
scores, recommendation constraints, and gates.

## Phase 5 — Reviewed cases and report

### P5.1 Reviewed local cases — Complete

- Nine source-backed reviewed cases are validated as a complete local library.
- Matching is deterministic and rejects fabricated companies, metrics, or sources.

### P5.2 Persisted Markdown planning report — Complete

- Structured narration is generated in bounded stages.
- Markdown rendering preserves confirmed facts, reviewed-case attribution,
  deterministic recommendation, scores, and gates.
- Unsupported numeric and KPI claims are rejected.

## Phase 6 — Product UI and case-centred workflow

### P6.1 Home, history, and model settings — Complete

- Streamlit uses the public FastAPI HTTP boundary.
- Product pages hide secrets, raw JSON, internal IDs, API URLs, and developer controls.

### P6.2 Brief, confirmation, and interview — Complete

- The durable Discovery flow supports correction, confirmation, interview rounds,
  refresh recovery, and a project-bound tested model profile.

### P6.3 Analysis and readable report views — Complete

- Results and persisted Markdown are restored through the public API.
- UUIDs, fact tokens, option keys, raw provider data, and technical diagnostics remain
  outside the product surface.

### P6.4 Discovery UX closeout — Complete, merged in PR #20

- Four global entries only: Home, New project, Project history, and Model settings.
- Discovery, assessment, and report are internal project-workspace stages.
- New-project and copy flows preserve only user-authored brief data and model binding.

### P6.5 Case-centred results closeout — Complete, merged in PR #22

The formal path is:

user needs → reviewed-case matching → case reference value → project-case fit →
critical gaps → transferable practices → hard-gate impacts → phased implementation.

API, persisted analysis, Results UI, and Markdown consume the same formal result.

### P6.6 Product Acceptance Baseline — Technical acceptance complete in PR #23

Delivered:

- four synthetic Traditional Chinese golden scenarios;
- typed fixtures and parameterized formal-result invariants;
- deterministic recommendation categories for AI hybrid, rules first, governed
  assistive, and readiness first routes;
- regression coverage for negation, high-impact employment signals, opportunity
  matching, case traceability, gates, refresh, and idempotency;
- NVIDIA-compatible headed Chrome UAT across all four full workflows.

Verification baseline:

- `601 passed, 6 skipped` before the final documentation/refactor closeout;
- Ruff, formatting, diff checks, and GitHub Actions passed;
- no critical failure and no duplicate formal PlanningRun was observed;
- provider narrative fallback and case-library gaps remain explicitly recorded.

The product-owner review of exact Traditional Chinese wording and business usefulness
was not performed after the owner lost access to a usable local UI session. It is
**deferred, not claimed as passed**, and is included in P8.1. P6 implementation work is
otherwise closed; P6.6 is an acceptance baseline, not another product feature.

### P6.7 Results Narrative and Comparison Redesign — Complete on feature branch

Delivered:

- a continuous enterprise assessment article with the executive conclusion before
  technical score and gate details;
- persisted interview findings, current/target comparison, candidate-option comparison,
  reviewed-case comparison, recommendation, roadmap, boundaries, and a safe technical
  appendix without standalone next actions;
- SQLite-reviewed solution patterns and source-backed case content; approved catalog
  records are the only formal source for user-facing solution names, case facts, and
  source links;
- deterministic solution–case–project consistency checks that reject mismatched
  recommendation categories, unapproved content, unrelated cases, and stale case facts;
- one canonical `ReportSynthesis` consumed by both the Results UI and Markdown;
- deterministic fallback composition when provider narrative generation is unavailable;
- regression tests for safe interview tracing, formal recommendation categories,
  provider fallback, no rerun on re-entry, UI/Markdown parity, and appendix-only scores
  and hard-gate identifiers.

Verification:

- the populated permission-request UAT uses a fresh persistent state root and artifact
  directory, with schema `8`, `ReportSynthesis` `2.2`, three approved matching cases,
  and three persisted interview findings;
- API first/refresh/history downloads are byte-identical; UI first/history downloads
  are byte-identical and line-for-line identical to the API report;
- refresh and history re-entry issue report reads only, with no report-generation POST;
- `622 passed, 6 skipped`, Ruff, formatting, and diff checks passed;
- headed Chrome verified the Results UI's integrated comparison chapter and download
  flow without standalone case cards or raw interview content.

### Checkpoint P6

- P6.1–P6.6 implementation and technical acceptance are complete.
- The four golden scenarios are the regression baseline for future providers.
- Final owner-facing language and portfolio review remains P8 work.

## Phase 7 — Local runtime and provider compatibility

### P7.1 Local Runtime Prerequisite — Complete, merged in PR #21

Delivered:

- project-owned `.venv` enforcement and runtime identity checks;
- dynamic API/UI ports with Local/Uat state isolation;
- safe start, status, and stop lifecycle for FastAPI and Streamlit;
- browser launch, supervised processes, and safe logs.

The previous roadmap items for separate install/start and package stop scripts are
**superseded by P7.1**. A consumer installer or release package is deferred.

### P7.2 Provider Compatibility and Local Inference — Next

Purpose:

- make existing project AI calls work consistently across the current cloud
  OpenAI-compatible baseline and one real local OpenAI-compatible endpoint first.

Required scope:

- explicit provider capabilities and safe profile validation;
- normalized token, authentication, structured-output, and response behavior;
- bounded structured-output fallback with strict validation;
- no silent provider or model fallback;
- project-bound profiles remain authoritative;
- reuse the P6.6 golden scenarios, beginning with one representative scenario before
  expanding to the full four-scenario matrix.

Acceptance:

- requirement understanding, interview, assessment narrative, and report narration
  work through the same application contracts;
- deterministic matching, recommendation categories, scoring, and hard gates remain
  provider-independent;
- provider failures are actionable and never expose API keys or raw responses;
- at least the existing NVIDIA-compatible endpoint and one local endpoint pass the
  agreed compatibility matrix.

Out of scope for P7.2:

- automatic model download or installation;
- support for every local runtime at once;
- Docker, cloud accounts, or release packaging.

## Phase 8 — Portfolio and release UAT

### P8.1 Execute viable-MVP acceptance review — Pending

Verify as a product owner:

- blocked-no-provider behavior and project-bound model selection;
- requirement understanding and interview usefulness;
- reviewed-case relevance, gaps, transferable practices, and phased path;
- report language and business usefulness, including deterministic fallback output;
- whether the six-dimension score adds user value or should remain secondary/hidden;
- launcher behavior, refresh/history recovery, and ignored-artifact hygiene;
- provider compatibility evidence from P7.2.

Fake-provider tests remain supporting evidence only.

## Known follow-ups

- Six live-provider integration tests remain opt-in because they require local secrets
  or endpoints.
- The reviewed-case library lacks strong expense-rule, IAM/governance, and
  image-based predictive-maintenance evidence.
- Provider narrative fallback behavior is a P7.2 compatibility input.

## Deferred

- consumer installer and release packaging;
- automatic llama.cpp or model installation;
- multi-agent, LangGraph, FAISS, and Docker;
- cloud deployment, accounts, online search, and multi-tenancy;
- production-grade credential encryption;
- PDF/DOCX export.
