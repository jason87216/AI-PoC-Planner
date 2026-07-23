# Viable MVP implementation plan

## Status

This plan supersedes the fake-model-first product roadmap. It starts from the
technical assets in `main`, but no phase is authorised by this documentation
reset until its checkpoint is approved.

## Guiding decisions

- A real OpenAI-compatible provider is a prerequisite for formal analysis.
- Fake providers are deterministic test doubles, never a public-product mode.
- Provider, durable project/version/conversation state, and fact validation are
  built before product UI work.
- The Streamlit UI remains the first product surface, but it follows the
  provider and workflow contracts rather than defining them.
- Each phase produces small, reviewable PRs. A checkpoint is a human approval
  gate, not merely a green test suite.

## Dependency sequence

```text
Phase 0 specification reset
  -> Phase 1 model profiles + real provider connection
  -> Phase 2 projects, versions, conversation, confirmed facts
  -> Phase 3 AI understanding + bounded interview
  -> Phase 4 AI recommendations + rubric + hard-gate validation
  -> Phase 5 reviewed cases + formal Markdown report
  -> Phase 6 Streamlit product UI
  -> Phase 7 install/start/stop entry points
  -> Phase 8 portfolio UAT and release readiness
```

Phases 1–5 are sequential. Phase 6 can begin only once Phase 3 contracts are
stable, but its analysis/report screens wait for Phases 4–5. Phase 7 waits for
the production-shaped API/UI launch contract. Phase 8 waits for all prior
checkpoints.

## Phase 0 — Specification reset

| Item | Definition |
| --- | --- |
| Input | PR #8 UAT findings and current technical baseline |
| Modification scope | README, project log, specification, plan, and tasks only |
| Output | Approved viable-MVP product contract and deprecation record |
| Automated test | Markdown links/commands and `git diff --check` review |
| Human UAT | Product owner verifies real provider precedes UI and fake flow is not MVP proof |
| Checkpoint | Explicit approval before any code branch |

## Phase 1 — Real model profile and OpenAI-compatible connection

| Item | Definition |
| --- | --- |
| Input | Approved profile contract and ignored-local-config decision |
| Modification scope | Provider/profile contracts, local JSON repository, API status/test endpoints, adapter, tests; no interview/report/UI rewrite |
| Output | CRUD model profiles, selected-profile status, connection test, and a formal-analysis guard |
| Automated test | Contract/repository/API tests; opt-in llama.cpp integration test; fake tests stay offline |
| Human UAT | Create/select/test a local llama.cpp profile with empty API key; failed/no profile blocks formal analysis |
| Checkpoint | A real endpoint is demonstrably called; no automatic fake fallback |

## Phase 2 — Project versions, visible conversation, and confirmed facts

| Item | Definition |
| --- | --- |
| Input | Phase 1 provider status and approved data-model design |
| Modification scope | Pydantic contracts, persistence/repository/migration, service/API tests |
| Output | Projects, immutable completed versions, visible conversation, fact confirmation/reference status |
| Automated test | Version immutability, reload, fact protection, contradiction/missing-data validation |
| Human UAT | Create a project, reload it, and change a completed plan into a new version |
| Checkpoint | Durable state can support the interview without exposing internal IDs |

## Phase 3 — AI requirement understanding and bounded interview

| Item | Definition |
| --- | --- |
| Input | Phase 1 real adapter and Phase 2 durable conversation/facts |
| Modification scope | Interview prompts/contracts, application service/API, provider tests; no scoring/report overhaul |
| Output | Initial brief, AI understanding/confirmation, at most three rounds of at most three contextual questions, user corrections |
| Automated test | Prompt-output schema validation, bounded rounds/questions, unknown answer, correction, no-chain-of-thought persistence |
| Human UAT | A real model asks context-specific questions and updates facts after correction |
| Checkpoint | Confirmed-fact and conversation UX is product-credible before analysis is added |

## Phase 4 — AI options, rubric scoring, and hard-gate validation

| Item | Definition |
| --- | --- |
| Input | Confirmed facts and bounded interview completion |
| Modification scope | Analysis contracts, AI rubric response validation, deterministic total/gates, API tests |
| Output | AI/non-AI/hybrid options, six fact-backed ratings, data gaps/risks/improvement conditions, enforced gates |
| Automated test | Score range/reference completeness, weighted total, invalid/contradictory evidence, every hard-gate conflict |
| Human UAT | Real-model output can recommend non-AI or hybrid and cannot bypass gates |
| Checkpoint | Analysis is useful and governed, not a fixed-rule simulation |

## Phase 5 — Local success cases and formal report

| Item | Definition |
| --- | --- |
| Input | Valid analysis and approved manually reviewed case format |
| Modification scope | Case data/validation/filtering, report assembly/rendering, tests |
| Output | Source-backed local cases and full Markdown report contract |
| Automated test | Case schema/review status, no invented source/metric fields, report section and fact-reference completeness |
| Human UAT | Business reviewer judges the report actionable, including cost assumptions, roles, deployment comparison, and next steps |
| Checkpoint | Report is a planning deliverable rather than technical score output |

## Phase 6 — Streamlit product UI

| Item | Definition |
| --- | --- |
| Input | Stable Phase 1–5 APIs and product contracts |
| Modification scope | Streamlit product pages and thin HTTP client only; no business-rule recomputation in UI |
| Output | Home/history, model settings, brief, confirmation, interview, analysis, and report views |
| Automated test | Client/error/smoke tests plus no direct persistence/application/provider imports |
| Human UAT | Complete a real-model flow without seeing UUIDs, raw JSON, API URLs, or developer warnings |
| Checkpoint | Product usability passes before launcher work |

## Phase 7 — Install, start, and stop entry points

| Item | Definition |
| --- | --- |
| Input | Stable local API/UI launch contract |
| Modification scope | Windows batch entry points, local configuration/bootstrap, smoke tests/docs |
| Output | Install/start/stop scripts that manage local FastAPI and Streamlit processes |
| Automated test | Script/static checks and controlled local smoke where feasible |
| Human UAT | Fresh Windows user installs, starts one command, sees no email prompt/telemetry, and stops reliably |
| Checkpoint | No manual two-terminal startup remains |

## Phase 8 — Portfolio UAT and release preparation

| Item | Definition |
| --- | --- |
| Input | All prior checkpoints and a manually started real provider |
| Modification scope | Documentation, acceptance evidence, safe sample data, release-only fixes |
| Output | UAT evidence and an honest public README |
| Automated test | Full suite, lint, formatting, security/ignored-artifact review |
| Human UAT | End-to-end viable-MVP flow, connection failure, non-AI recommendation, reload/versioning, and report review |
| Checkpoint | Product owner approves release candidate |

## Testing policy

| Layer | Purpose |
| --- | --- |
| Unit/contract | Pydantic schemas, fact references, score bounds, gates, case/report validation |
| Repository/service | Local JSON profiles, project/version/conversation persistence, immutable version transitions |
| API | Profile status/testing, formal-analysis guard, interview/analysis/report response contracts |
| Fake-provider | Deterministic automated behavior only; no claim of product usefulness |
| Opt-in integration | Manually running llama.cpp server; never default CI prerequisite |
| UI | Thin-client/smoke coverage and human real-model UAT |

## Definition of done

The viable MVP is done only when a user can select a tested real model profile,
complete the confirmation/interview flow, obtain a fact-backed AI/non-AI/hybrid
recommendation constrained by hard gates, save/reopen an immutable project
version, and export an actionable Markdown report through the product UI and
single-machine launch flow. A fake-model path alone never satisfies this
definition.
