# Project Log

## Current goal

P6.4 Discovery UX closeout is complete; P6.5 is next.

## Current status

- `main` has the first Streamlit product surface, but is not yet a complete
  viable end-user product.
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
  correction contract.
- Phase 4 upgrades SQLite additively to schema v5. It keeps legacy,
  Phase 2, and Phase 3 records intact while adding immutable analysis results,
  options, scores, resolved current-fact references, and hard-gate results.
  The provider proposes structured options and ratings only; the program
  validates current `Fxxx` fact references, assigns the six normative weights,
  calculates the weighted total, and applies existing HG-01 through HG-07 with
  conservative handling for unknown gate inputs. No prompt, reasoning, raw
  response, API key, Authorization header, or base URL is persisted. Options
  are generated through an A0 recommendation index followed by kind-specific
  A1 details; the application derives the formal conclusion from the selected
  kind. Offline validation and two real NVIDIA NIM `openai/gpt-oss-20b` UAT
  runs passed with `json_schema`, `reasoning_effort=low`, temporary state, and
  production APIs. Phase 5 cases/reports and the Streamlit rebuild have not
  started.
- Phase 5.1 adds a read-only `data/reviewed_cases.json` library with nine
  manually reviewed source-backed cases covering the existing opportunity
  catalog. Its Pydantic contracts reject invalid records as a complete-library
  failure; deterministic matching uses approved status, exact opportunity type,
  applicability/non-applicability tags, evidence grade, and stable case ID.
  It does not call a provider, search online, write SQLite, change assessment
  scores/gates.
- Phase 5.2 is implemented on schema v6 with an immutable `planning_reports`
  table, validated structured report DTOs, and a fixed-order deterministic
  Markdown renderer. Eighteen narration fields are generated in staged Report
  Part A and Report Part B calls; the renderer preserves program-owned
  conclusion, scoring, hard-gate values, fact references, and reviewed-case
  attribution. Numeric claims and KPI thresholds are rejected unless
  fact-backed. Report-only NVIDIA NIM UAT passed twice with fresh temporary
  state, including POST completion, GET, duplicate blocking, and fresh-app
  reload. Full cross-phase UAT is deferred to Phase 8.
- Phase 6.1 adds a Streamlit entry point with home, project-history, and
  model-settings pages. Every read and mutation uses a thin HTTP client over
  the public FastAPI boundary; the UI imports no application, persistence, or
  provider layers. It shows human-readable project/model state, keeps API keys
  password-masked and non-retrievable, and avoids UUIDs, raw JSON, API URLs,
  and developer diagnostics.
- Phase 6.2 adds a Streamlit Phase 3 discovery surface: a minimal formal brief,
  real-provider requirement understanding, correction/regeneration,
  confirmation, and API-state-driven bounded interview rounds. It restores the
  latest discovery item on rerun, renders the completed fact summary without
  technical identifiers, and never imports application, persistence, or
  provider layers. Real NVIDIA NIM `openai/gpt-oss-20b` browser UAT passed with
  `json_schema`, `reasoning_effort=low`, a tested selected temporary profile,
  a correction, an unknown answer, a proactive fact addition, three bounded
  rounds, ready-for-assessment, and page-refresh recovery.
- Phase 6.3 adds a read-only results surface for persisted Phase 4 analysis and
  Phase 5 reports. It uses only public FastAPI HTTP endpoints, follows durable
  project status, creates writes only from explicit buttons, and recovers the
  latest result-capable project after refresh. It renders options, six scores,
  hard gates, risks, gaps, all eighteen report sections, and saved reviewed-case
  sources without UUIDs, fact tokens, raw JSON, API URLs, SQLite paths, prompts,
  or technical diagnostics. The Markdown download is the persisted UTF-8 report,
  not a UI re-render. Real NVIDIA NIM `openai/gpt-oss-20b` browser UAT passed
  with `json_schema`, `reasoning_effort=low`, temporary state, assessment,
  Report Part A/Part B, completed refresh, and Markdown download. Phase 6 is
  complete; full cross-phase UAT remains deferred to Phase 8 and Phase 7 has not
  started.
- Phase 6.4 removes fact-level governance controls from the product Discovery
  UI. Natural-language feedback and a free supplementary note preserve revisions
  at the FastAPI boundary without exposing fact IDs or keys. Prompts require
  Traditional Chinese and limit questions to material direction, gate, scope,
  deployment, and human-review decisions. P6.5 navigation, results, and
  error-state closeout remains pending; Phase 7 has not started.
- P6.4 human-UAT follow-up keeps the selected project name, version, and phase
  as the Discovery-page context; renders complete AI understanding in a bordered
  card with concise confirmation/modification controls; and removes normal-flow
  interview transition pages by generating questions inline after confirmation
  and saved answers. Its prompts require fuller Traditional Chinese
  understanding and prioritize reviewed-case matching/gap inputs. P6.5 remains
  unstarted: its documented direction is case-centred assessment, separating
  case reference value, project-case fit, and critical gaps rather than having
  AI score its own generated option.

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
