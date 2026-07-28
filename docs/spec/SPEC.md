# Specification: AI PoC Planner viable MVP

## Status

This document resets the product specification after PR #8 product UAT. It is
documentation only: no implementation is authorized by this reset.

The previous decision that a repeatable fake-model vertical slice represented a
successful product MVP is revoked. A fake model remains a test fixture only.

## Objective

AI PoC Planner is a local-first enterprise AI adoption discovery and PoC
planning tool. It connects to a real OpenAI-compatible chat API, interviews a
user about a business problem, protects confirmed facts, applies programmatic
governance constraints, and produces an actionable Markdown PoC plan.

The first supported real-provider path is a user-operated llama.cpp server.
The product does not install llama.cpp or download a GGUF model.

## Goals

- Require a working real model connection before formal AI analysis.
- Let a user create, edit, delete, test, and select local model profiles.
- Collect a minimal initial brief, then conduct a bounded, contextual interview.
- Persist projects, versions, user/AI visible conversation, confirmed facts, and
  completed reports locally.
- Allow an outcome that recommends AI, non-AI, foundational non-AI work first,
  or a hybrid approach.
- Produce a readable, business-actionable Markdown report.

## Non-goals

- Multi-agent workflows, LangGraph, FAISS, Docker, cloud deployment, accounts,
  multi-tenancy, email login, automatic model download, or llama.cpp management.
- React/Next.js, PDF/DOCX export, online case search, and production-grade
  credential encryption.
- Any autonomous high-impact business, medical, legal, credit, or financial
  decision.

## Users and user stories

| User | Story |
| --- | --- |
| Business owner | I can describe a problem, confirm the AI's understanding, correct it, and receive a plan I can act on. |
| PoC lead | I can compare AI, non-AI, and hybrid options with cited facts, risks, cost assumptions, and next steps. |
| Local operator | I can manage several OpenAI-compatible model connections and verify the selected connection before analysis. |
| Reviewer | I can open a historical project version, see the visible conversation and confirmed facts, and understand why its recommendation was made. |

## Product flow

1. The home page shows model connection status, new planning, and historical
   project versions without exposing UUIDs or run IDs.
2. The user selects a tested model profile and submits a minimal initial brief.
3. The AI returns a requirement understanding; the user confirms or corrects it.
4. The AI asks at most three rounds of at most three contextual questions per
   round. Every question includes why it matters, affected judgement, and an
   example. The user may answer `不知道` and may proactively correct or add facts.
5. The AI updates structured facts. The program validates structure, protects
   confirmed facts, checks contradictions and missing data, and then enables
   analysis.
6. The AI proposes AI, non-AI, or hybrid directions; the program calculates the
   weighted total and applies hard gates.
7. The product displays and exports a Markdown planning report. A completed
   version is immutable; subsequent edits create a new version.

## Functional requirements

### Model profiles and provider boundary

- A profile contains `profile_name`, `base_url`, `model_name`, and optional
  `api_key`.
- Profiles, including API keys, are stored in a local ignored JSON file in MVP.
- The UI supports create, edit, delete, test, select, and current-status views.
- The application uses an OpenAI-compatible adapter. llama.cpp is the first
  documented opt-in integration target.
- Formal analysis must reject requests when no tested real profile is selected.
- The runtime must never silently fall back to a fake model. Fake providers are
  allowed only in automated tests.

### Initial brief, conversation, and facts

The initial form requires: project name, current problem/workflow, desired
outcome, and available data. Available data accepts `不知道` or `目前没有`.
Users and owners plus known constraints are optional. There is no catch-all
"supplementary notes" input.

The persisted visible conversation records user messages, AI requirement
understanding, confirmations/corrections, questions, and answers. It does not
store system prompts, chain of thought, LangChain trajectories, or raw provider
metadata.

Confirmed facts are structured Pydantic data. The program validates reference
completeness, preserves confirmed facts until a user correction, detects
contradictions, and marks unknown or missing data. The AI may infer a proposed
fact but must label it as an assumption until the user confirms it.

### Project and version model

- The home page presents project name, version, status, created/updated time,
  and selected model profile.
- UUIDs may remain internal but never appear in the primary product UI.
- A completed version cannot be overwritten. Editing it creates the next version
  under the same project.

### Analysis, opportunities, and scoring

The existing nine AI opportunity catalog categories remain. The AI can propose
an external category only when it is labelled `unstandardized_candidate`.

The three retained non-AI directions are `rule_based_automation`,
`conventional_software`, and `data_analytics`. Allowed conclusions are:

- suitable for AI;
- better suited to non-AI;
- establish non-AI foundations before AI; or
- hybrid AI and non-AI.

The six dimensions remain: business value, data readiness, technical fit,
architecture controllability, governance readiness, and user adoption. Each
dimension contains a 1–5 score, rationale, referenced confirmed facts, data
gaps, risks, and conditions required to improve the score.

AI owns requirement understanding, factual organisation, assumptions and
contradictions, questions, constrained option/narrative content, and report
writing. Program code owns reviewed-case matching/ranking, case reference value,
project-to-case fit, gap comparison, transferable-practice provenance,
persistence, Pydantic validation, score calculation, fact-reference validation,
confirmed-fact protection, consistency checks, weighted-total calculation,
hard-gate enforcement, and profile management.
Program code must not use the old fixed Boolean rules to decide a final
dimension rating.

Existing hard gates remain mandatory for unauthorised data use, autonomous
high-impact decisions, forbidden external processing, missing required human
review, and other explicit safety/governance conflicts. AI cannot override a
hard-gate result.

### Case-centered assessment semantics

Reviewed cases are primary assessment evidence, not an appendix. Only approved
cases may enter formal ranking. Case reference value measures source clarity,
review status, evidence/results, context completeness, and recorded limits. It
is separate from project-to-case fit, which compares confirmed project facts
with workflow, responsibility, system, input, governance, decision, deployment,
and first-stage scope dimensions. Unknown facts remain neutral/unknown and are
shown as confirmation work; they are never silently treated as pass or fail.

The six dimensions evaluate the current project's feasibility and readiness for
an implementation path at its present stage. They do not evaluate an AI-created
option as if that option were a product. Hard gates constrain stage, capability,
automation level, and deployment scope; a gate may still permit local,
assistive, deterministic, or human-reviewed work. The API analysis snapshot is
the single formal result consumed by the Results workspace and Markdown report.

### Local success cases

MVP uses a local, manually curated, source-backed case library. SQLite is the
runtime source of truth for approved solution patterns and reviewed cases. A
solution pattern has an immutable key, recommendation category, reviewed
Traditional-Chinese display name and description, suitable/unsuitable scope,
human boundary, expected outputs, acceptance focus, review status, and content
version. Only an approved pattern may enter a formal report; provider option
titles are never reader-facing formal names.

A reviewed case has reviewed Traditional-Chinese title, context, implementation,
recorded outcome, transferable practice, limitation, source name and URL,
solution-key applicability, conditions, evidence grade, review status, and
content version. Approved cases require a valid source URL. AI must not
fabricate, translate, or overwrite companies, case facts, metrics, titles, or
sources. Matching first requires an approved solution-key relationship, no
opportunity/condition/hard-gate conflict, and only then applies deterministic
fit and gap comparison. FAISS is not required.

A controlled permission-request route requires confirmed evidence of an access
request, fixed rule checks, and human approval together. It maps to the
approved governed access solution pattern even when validation samples are not
yet available; a generic mention of access or knowledge material is
insufficient. This prevents data-readiness gaps from obscuring the project's
actual rules-and-approval workflow.

### Report contract

The canonical `ReportSynthesis` contains: project evaluation summary; the
reviewed formal recommendation and rationale; concise interview findings;
integrated solution/case/project-gap comparison; implementation roadmap, risks,
and acceptance; and a technical appendix. The comparison presents the reviewed
solution, each matching reviewed case with a named source link, then the
solution/case table and current/target/gap table. It may state that no sufficient
reviewed case exists; it must not force an unrelated case. UI and Markdown use
the same persisted synthesis and source links.

The UI renders the readable report first. Raw Markdown, IDs, rule IDs, and
technical evidence are not primary product content.

## UI boundaries

Phase-one UI remains Streamlit, with home, model settings, initial brief,
requirement confirmation, interview, analysis results, and report views.

The formal UI must not display run IDs, UUIDs, API base URLs, correlation IDs,
SQLite paths, raw JSON, fake-mode warnings, or technical architecture
disclaimers. Portfolio context and technical limitations belong in the README.

## Non-functional requirements

- Local-first, single-user operation with durable local storage.
- Explicit timeouts and safe user-facing provider errors; no secret leakage.
- Model/profile data stays in ignored local files; API keys may be empty.
- Deterministic automated tests use a fake provider and make no real network
  calls. Real-provider integration tests are opt-in.
- Formal analysis is blocked, not simulated, without a real selected profile.
- Visible conversation and completed reports must survive restart/reload.

## Installation and startup requirements

Phase-seven deliverables are `安装 AI PoC Planner.bat`, `启动 AI PoC Planner.bat`,
and `停止 AI PoC Planner.bat`.

- Install checks Python 3.12, creates `.venv`, installs dependencies,
  initialises local storage/data directories, creates Streamlit configuration,
  and disables first-run email collection and usage telemetry.
- Start launches FastAPI, waits for health, launches Streamlit, opens a browser,
  and does not require two manual PowerShell windows.
- Stop reliably terminates the two local processes.

## Data model direction

Future implementation will add model profiles, projects, immutable project
versions, visible conversation entries, structured facts with confirmation
status and references, analysis, report exports, and reviewed success cases.
Schema design is deferred to the corresponding implementation phases; this
specification authorises no migration.

## Acceptance criteria for the viable MVP

1. A selected, tested real OpenAI-compatible profile is required for formal
   analysis; absent/failed connection blocks it with a safe explanation.
2. llama.cpp can be manually started and tested through the documented opt-in
   integration path.
3. A user can complete the bounded confirmation/interview flow, including
   unknown answers and corrections, and reload visible conversation/facts.
4. Results can honestly recommend AI, non-AI, foundations-first, or hybrid.
5. Scores cite confirmed facts; program validation rejects invalid ranges,
   missing fact references, contradictions, and hard-gate violations.
6. A completed version is immutable and a subsequent change creates a version.
7. A readable Markdown report contains every report-contract section.
8. The primary UI exposes no developer controls or internal identifiers.
9. Automated tests use fakes only as test infrastructure; they are not product
   acceptance proof for real-model analysis.

## Revoked decisions

- Fake-model vertical-slice completion is not MVP completion.
- Fixed scripted clarification fields are not a viable interview experience.
- Fixed Boolean business rules do not own final rubric ratings.
- FAISS, Docker, and a live provider are not represented as completed features.
