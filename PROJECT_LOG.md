# Project Log

## Current goal

Complete Phase 3 real-model discovery interview; do not begin Phase 4.

## Current status

- `main` is a technical foundation, not a viable end-user product.
- PR #8 passed automated validation but failed manual product UAT.
- The failure is not a single implementation bug: the previous MVP acceptance
  standard incorrectly treated a repeatable fake-model vertical slice as product
  success.
- The replacement direction is a local-first tool using a real
  OpenAI-compatible provider, first targeting a user-started llama.cpp server.
- `feat/model-profile-contracts` now contains Phase 1 only: P1.1 contracts,
  local JSON profiles, OpenAI-compatible adapter, status/readiness API, and an
  opt-in llama.cpp test. It does not start Phase 2 conversation/version/fact
  work, rebuild Streamlit UI, or connect the old planning prototype to a fake
  runtime fallback.
- Real llama.cpp UAT passed using `D:\ai_class\tools\llama-cpp\bin\llama-server.exe`
  with `Qwen3-8B-Q4_K_M.gguf`, bound only to `127.0.0.1` with an empty API key.
  The integration test plus profile CRUD, selection, connection test, readiness,
  invalidation, and fresh-process status reset all passed; there was no fake
  runtime fallback and no Phase 1 code bug.
- Phase 2 uses schema v3 with additive migration from legacy v1/v2 schemas.
  Existing `analysis_projects` and `planning_runs` remain legacy prototype
  tables; new `planning_projects`, linear immutable versions, visible messages,
  append-only fact revisions, and fact/message references form the viable-MVP
  aggregate. Local API UAT passed create/reload, completion, successor cloning,
  fact confirmation/correction, unknown/missing facts, and completed-version
  blocking without any provider call or fake runtime fallback.
- Phase 3 upgrades SQLite additively to schema v4. It retains every legacy and
  Phase 2 table, and adds `planning_interview_sessions` plus
  `planning_interview_questions` for a bounded, reloadable discovery flow.
  The flow requires a selected, enabled, tested real profile; creates a minimal
  initial brief with confirmed/unknown/missing facts; validates real-model JSON
  understanding before user confirmation; and supports explicit correction plus
  at most three interview rounds of at most three visible questions. No prompt,
  reasoning, raw provider response, API key, or Authorization value is stored.
  Offline validation and the real Qwen3 llama.cpp UAT passed using
  `--reasoning off`, empty API key, and loopback-only server binding. The UAT
  covered initial brief, correction/regeneration, confirmation, bounded rounds,
  unknown/addition/correction, ready-for-assessment, and fresh-app reload. It
  exposed and fixed a local structured-output timeout and an over-specified
  correction contract. Phase 4 scoring, hard gates, cases, reports, and the
  Streamlit rebuild have not started.

## UAT findings recorded from PR #8

- The public flow used `ScriptedDemoChatModel`, not a real provider.
- User input was not meaningfully interpreted and scripted results could still
  be produced.
- Clarification questions were fixed-field templates without sufficient context
  or example guidance.
- The primary UI exposed run IDs, API URL/developer controls, correlation
  details, raw JSON, and fake-mode messaging.
- Installation/startup required undocumented manual environment and two-process
  work.
- Initial Streamlit startup showed an email prompt.
- The proposal/report primarily exposed technical scores/rules rather than an
  actionable business planning document.

## Decisions retained

- Python, FastAPI, Streamlit, SQLite, Pydantic, pytest, and Ruff remain the
  local-first technical base.
- LangChain remains an optional single-agent integration boundary; no multi-agent
  or LangGraph work is authorised.
- The existing six dimensions, weighted-total calculation, hard gates, nine AI
  opportunity categories, and three non-AI directions are retained as assets
  subject to the new ownership rules.
- Deterministic fake providers remain offline test infrastructure.

## Decisions revoked

- A fake-model vertical slice is not viable-MVP acceptance.
- A public scripted fake mode is not an acceptable substitute for a real model.
- Fixed Boolean rules do not own final AI rubric ratings.
- FAISS, Docker, or live-provider runtime must not be described as completed.

## Approved next sequence after specification review

1. Model profile contract, ignored local JSON repository, OpenAI-compatible
   adapter, connection test/status API, and opt-in llama.cpp test.
2. Project version, visible conversation, and confirmed-fact persistence.
3. Real-model requirement understanding and bounded contextual interview.
4. AI options/rubric output plus programmatic validation and hard gates.
5. Local reviewed cases, formal Markdown report, product UI, and launchers.

## Git notes

- PR #8 is retained as a technical prototype/experiment record and is not a
  release candidate.
- PR #11 merged Phase 1 after real llama.cpp UAT. PR #12 merged Phase 2.
  Phase 3 is in progress on `feat/real-model-interview`; do not begin Phase 4.

## Known open questions for later code design

- Exact local profile JSON location and migration path from test fixtures.
- Project/version/conversation schema and fact-reference representation.
- Which llama.cpp OpenAI-compatible endpoint behaviours are mandatory for the
  opt-in integration test.
- Cost-estimate assumptions and reviewed success-case source policy.
