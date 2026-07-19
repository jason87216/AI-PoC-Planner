# Spec: AI PoC Planner

## 1. Status and Assumptions

- Status: version 1 implementation baseline, approved by the user on 2026-07-19.
- Product form: local web application with FastAPI API and Streamlit UI.
- Primary language: Traditional Chinese; schema field names and code identifiers use English.
- Runtime/package manager: Python 3.12 with standard `pip` commands; `pyproject.toml` is the sole package configuration source.
- Model access: an internal provider adapter, with OpenAI-compatible API as the default integration shape.
- Persistence: SQLite for business data and FAISS for case embeddings.
- Authentication, multi-tenancy and cloud deployment are outside MVP.
- Legal and compliance results are planning warnings, not legal advice.

## 2. Objective

Build a public, testable AI engineering portfolio project that converts an ambiguous business request into a structured, evidence-supported AI PoC proposal. The system must interview the user, preserve state, identify missing information, retrieve local cases, run deterministic assessments, apply hard gates, return a validated proposal and export Markdown.

Success means a reviewer can run the fake-model path locally and reproduce the vertical slice:

`建立專案 → 完成訪談 → 執行評估 → 產生並匯出報告`

## 3. Goals and Non-goals

### Goals

- One standard structured interview that gathers business, data, technical, governance, ROI and KPI inputs.
- One LangChain Agent that selects among bounded, local assessment tools.
- Durable conversation state and audit records in SQLite.
- Similar-case retrieval from a local FAISS index with metadata in SQLite.
- Deterministic weighted scoring and risk hard gates.
- Pydantic-validated PoC proposal and Markdown export.
- FastAPI and Streamlit interfaces over the same application services.
- Fully offline, deterministic tests through a fake model.

### Non-goals

- Multiple agents or autonomous agent teams.
- Executing actions in real enterprise systems.
- Generic chatbot behavior outside the interview flow.
- Complex authentication or authorization.
- Multi-tenant SaaS.
- PostgreSQL, pgvector, Qdrant or cloud vector databases.
- Cloud deployment.
- Automated financial, employment, medical, legal or credit decisions.
- Claiming legal compliance or replacing professional review.

## 4. User Roles

| Role | Need | MVP capability |
|---|---|---|
| AI／Solution Engineer | Convert business context into a bounded technical PoC | Interview, case retrieval, architecture and scope proposal |
| AI consultant | Produce a consistent, explainable first-pass assessment | Scoring rationale, hard gates, Markdown report |
| Digital transformation／technical PM | Clarify owner, KPI, ROI, data and delivery constraints | Structured interview and missing-information follow-up |
| Reviewer／portfolio evaluator | Verify engineering quality without a paid model account | Fake-model vertical slice, pytest and documented contracts |

## 5. User Stories

- As a planner, I can create an analysis project with a title and initial problem statement.
- As a planner, I can answer a standard interview over multiple turns without losing prior answers.
- As a planner, I am asked only for information that is still missing or contradictory.
- As a planner, I can see which similar cases support the recommendation.
- As a planner, I receive separate results for data readiness, technical fit, architecture control, governance, ROI/KPI and adoption.
- As a reviewer, I can see hard-gate results independently from the weighted score.
- As a reviewer, I can reproduce why each score and recommendation was produced.
- As a planner, I can export the final proposal as Markdown.
- As a developer, I can test the complete flow with a deterministic fake model and no network.

## 6. Product Flow

1. Create an AI adoption analysis project.
2. Start a structured interview session.
3. Persist every accepted user answer and conversation-state snapshot.
4. Detect missing or contradictory information and ask up to five high-information questions per turn.
5. Search the local case knowledge base.
6. Evaluate data readiness, technical feasibility, risk, ROI and KPI quality.
7. Apply risk hard gates before interpreting weighted scores.
8. Produce a Pydantic-validated PoC proposal.
9. Render and export a Markdown report.

## 7. Functional Requirements

| ID | Requirement | Acceptance signal |
|---|---|---|
| FR-01 | Create and read an analysis project | Project has stable UUID, timestamps and status |
| FR-02 | Start one standard interview flow | Session references exactly one project |
| FR-03 | Persist turns and normalized answers | Reloading from SQLite reconstructs state |
| FR-04 | Detect gaps and contradictions | Result lists missing fields and follow-up questions with reasons |
| FR-05 | Limit follow-up questions | A turn returns at most five questions |
| FR-06 | Retrieve similar local cases | Results include case ID, title, score and source reference |
| FR-07 | Run six deterministic assessment tools/services | Same input produces the same non-model scores and gates |
| FR-08 | Apply hard gates first | Gate result cannot be overridden by weighted score |
| FR-09 | Calculate six-dimension weighted score | Weights total 100 and inputs are integers 1–5 |
| FR-10 | Produce structured proposal | Output passes `PocProposal` validation |
| FR-11 | Export Markdown | Export includes input summary, evidence, scores, gates, proposal and next actions |
| FR-12 | Provide fake-model mode | Complete vertical slice runs without network or API key |
| FR-13 | Keep an audit trail | Assessment records include rule version, case IDs and rationale |

## 8. Non-functional Requirements

- NFR-01 Reproducibility: fake-model tests must not access the network.
- NFR-02 Determinism: scoring, hard gates, ROI math and report section ordering are deterministic.
- NFR-03 Validation: every external boundary uses Pydantic validation.
- NFR-04 Explainability: every score, gate and recommendation stores machine-readable rationale.
- NFR-05 Privacy: raw interview data, databases, FAISS indexes and traces are ignored by Git.
- NFR-06 Provider portability: domain, repository and scoring modules import no provider-specific SDK.
- NFR-07 Local-first: MVP runs with SQLite and FAISS without an external database service.
- NFR-08 Testability: tool and application services are injectable and replaceable with fakes.
- NFR-09 Accessibility: Streamlit forms use clear labels, error summaries and keyboard-operable controls.
- NFR-10 Observability: logs contain correlation IDs but exclude secrets and raw sensitive answers by default.

## 9. Core Data Model

| Entity | Required fields | Notes |
|---|---|---|
| `AnalysisProject` | `id`, `title`, `problem_statement`, `status`, `created_at`, `updated_at` | Root aggregate |
| `InterviewSession` | `id`, `project_id`, `status`, `current_stage`, `state_version`, timestamps | One standard flow per active session |
| `InterviewTurn` | `id`, `session_id`, `sequence`, `role`, `content`, `normalized_answers`, timestamp | Raw content is local sensitive data |
| `ConversationStateSnapshot` | `session_id`, `version`, `known_fields`, `missing_fields`, `contradictions`, timestamp | Reconstructable, append-oriented audit snapshot |
| `CaseMetadata` | `id`, `title`, `industry`, `problem`, `fit_conditions`, `non_fit_conditions`, `pattern`, `risk_flags`, `kpis`, `human_review`, `source_path`, `content_hash`, timestamps | Stored in SQLite; vector ID maps to FAISS |
| `Assessment` | `schema_version`, `id`, `project_id`, `session_id`, `rule_version`, `scores`, `weighted_score`, `hard_gates`, `gate_disposition`, `recommendation`, case/evidence refs, `rationale`, timestamp | Immutable deterministic engine result |
| `PocProposalRecord` | `id`, `project_id`, `assessment_id`, `schema_version`, `payload`, timestamp | Payload must validate before storage |
| `ReportExport` | `id`, `project_id`, `proposal_id`, `format`, `content_hash`, `local_path`, timestamp | MVP format is Markdown only |

All IDs are UUID strings. Timestamps are timezone-aware UTC values. SQLite migrations and exact SQL schema are implementation decisions within the contracts above.

## 10. Pydantic Schema Contracts

These names and fields are normative. The snippet is documentation, not application code.

```python
from typing import Literal
from pydantic import BaseModel, Field


Recommendation = Literal["建議進行", "條件式建議", "暫不建議"]
GateDisposition = Literal["pass", "requires_controls", "assistive_only", "blocked"]


class ClarifyingQuestion(BaseModel):
    field: str
    question: str
    reason: str
    priority: int = Field(ge=1, le=5)


class ScoreDimensionResult(BaseModel):
    dimension: Literal[
        "business_value",
        "data_readiness",
        "technical_fit",
        "architecture_controllability",
        "governance_readiness",
        "user_adoption",
    ]
    rating: int = Field(ge=1, le=5)
    weight: int
    weighted_points: float = Field(ge=0, le=100)
    rationale: str
    evidence_refs: list[str]


class HardGateResult(BaseModel):
    rule_id: str
    disposition: GateDisposition
    reason: str
    required_controls: list[str]
    human_review_required: bool
    evidence_refs: list[str]


class SimilarCase(BaseModel):
    case_id: str
    title: str
    similarity: float = Field(ge=0, le=1)
    fit_summary: str
    source_ref: str


class ArchitectureOption(BaseModel):
    name: str
    summary: str
    deployment: Literal["local", "private-cloud", "on-prem"]
    components: list[str]
    assumptions: list[str]


class PocProposal(BaseModel):
    schema_version: Literal["1.0"]
    recommendation: Recommendation
    gate_disposition: GateDisposition
    problem_statement: str
    target_users: list[str]
    current_workflow_summary: str
    known_information: dict[str, str | int | float | bool | list[str] | None]
    missing_information: list[str]
    clarifying_questions: list[ClarifyingQuestion]
    similar_cases: list[SimilarCase]
    scores: list[ScoreDimensionResult]
    weighted_score: int = Field(ge=0, le=100)
    hard_gates: list[HardGateResult]
    architecture_options: list[ArchitectureOption]
    required_data: list[str]
    integrations: list[str]
    risks: list[str]
    human_review_points: list[str]
    roi_assumptions: list[str]
    success_metrics: list[str]
    estimated_weeks: int = Field(ge=1)
    estimated_team: list[str]
    next_actions: list[str]
```

Contract and engine invariants:

- Pydantic: `scores` contains each of the six dimensions exactly once.
- Pydantic: stored weights equal the normative weight table and total 100.
- M1.3 engine: `weighted_score` equals the deterministic recomputation from `scores`.
- M1.3 engine: `blocked` forces recommendation `暫不建議`.
- M1.3 engine: `assistive_only` or unsatisfied `requires_controls` caps recommendation at `條件式建議`.
- Pydantic: an `assistive_only` declared result requires at least one `human_review_point`.

M1.2 validation responsibility is structural: required fields, types, enums,
non-empty values, IDs, UTC timestamps, uniqueness, schema versions, six-dimension
completeness, normative stored weights and impossible declared-field combinations.
M1.3 owns the calculation of `weighted_points`／`weighted_score`, hard-gate rule
evaluation and precedence, score thresholds and the recommendation decision. The
contracts type-check M1.3 outputs; M1.3 engine tests validate business outcomes.

M1.3 adds an optional, backward-compatible formal-evaluation surface to
`AssessmentInput`: caller-supplied `assessment_id`, `evaluated_at`, typed
`AssessmentFacts`, and typed `AssessmentToolOutputs`. Workflow code may still use a
partial `AssessmentInput`, but `assess_project` rejects it until these four fields
are present. `AssessmentFacts` contains explicit Boolean, enum and bounded-count
signals for the six approved rubrics and gates; the engine never infers decisions
from free text. The tool bundle contains all six M1.2 output contracts, and any
missing or error-envelope output prevents formal evaluation.

Every score and gate evidence reference must resolve to the input evidence registry.
`EvidenceReference` may carry explicit `project_id` and `session_id` ownership; when
those optional fields are absent, ownership comes from the enclosing
`AssessmentInput`. Duplicate facts supplied through tool outputs and
`AssessmentFacts` must agree or formal evaluation fails with a stable error code.

## 11. Agent State Schema

The M1.2 `AgentState` is a framework-neutral Pydantic model. A future Agent adapter
may map or extend it with LangChain state types, while SQLite remains the durable
source of truth.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | version string | Serializable state contract version |
| `project_id` | `str` | Current aggregate |
| `session_id` | `str` | Current interview session |
| `session_project_id` | `str` | Standalone consistency reference; must equal `project_id` |
| `workflow_stage` | project-status enum | Project lifecycle stage independent from interview section |
| `interview_stage` | enum | `context`, `data`, `value`, `governance`, `review`, `complete` |
| `known_fields` | `dict[str, JSONValue]` | Normalized accepted answers |
| `missing_fields` | `list[str]` | Required information gaps |
| `contradictions` | `list[str]` | Conflicts requiring clarification |
| `questions_asked` | `list[str]` | Prevent duplicate follow-ups |
| `clarifying_questions` | `list[ClarifyingQuestion]` | Current typed follow-ups |
| `similar_case_ids` | `list[str]` | Retrieved evidence |
| `evidence_refs` | `list[UUID]` | Typed references to accepted evidence records |
| `tool_results` | `dict[str, JSONValue]` | Validated tool outputs |
| `hard_gate_disposition` | enum or null | Strongest gate seen |
| `assessment_id` | UUID or null | Required at assessed and later stages |
| `proposal_id` | UUID or null | Required at proposal-generated and completed stages |
| `proposal` | `PocProposal` or null | Final structured response |

State transitions must persist the accepted user turn before model/tool processing and persist the resulting normalized snapshot after processing. A failed model call must not erase the accepted turn.

## 12. Tool Interfaces

M1.4 defines a framework-neutral provider boundary. A model provider accepts a
typed `ProviderRequest` and returns a `ProviderPreparation` whose status is either
`ready` or `clarification_required`. A ready result contains `AssessmentFacts` and
all six typed tool inputs; a clarification result contains one to five typed
questions and no assessment payload. Providers never return formal scores,
weighted totals, hard-gate disposition, recommendation or evidence records. They
may only reference evidence supplied by the enclosing application request.

The minimal capability contract exposes structured-output, tool-calling and
streaming flags plus a model identifier. An independent `EmbeddingProvider`
protocol accepts a sequence of strings and returns typed vectors. M1.4 provides
deterministic offline fakes for both protocols; no SDK, registry or live endpoint
is introduced.

| Tool | Input contract | Output contract | Deterministic boundary |
|---|---|---|---|
| `retrieve_similar_cases` | `RetrieveSimilarCasesInput` | `RetrieveSimilarCasesOutput` containing cases and evidence refs | Embedding query may vary by provider; filtering and output schema are deterministic |
| `assess_data_readiness` | `AssessDataReadinessInput` | `AssessDataReadinessOutput` containing data-readiness result, gaps and prerequisites | Rules first; no free-form model score |
| `assess_technical_fit_and_architecture` | `AssessTechnicalFitAndArchitectureInput` | `AssessTechnicalFitAndArchitectureOutput` containing two scores and options | Must recommend simpler non-Agent pattern when sufficient |
| `evaluate_risk_and_hard_gates` | `EvaluateRiskAndHardGatesInput` | `EvaluateRiskAndHardGatesOutput` containing governance-readiness score, declared gates and aggregate disposition | M1.3 implements deterministic versioned rules |
| `assess_business_value_roi_and_kpis` | `AssessBusinessValueRoiAndKpisInput` | `AssessBusinessValueRoiAndKpisOutput` containing two scores, ROI assumptions and KPI proposals | M1.3 implements arithmetic and rubric; unknown values remain assumptions |
| `estimate_poc_scope` | `EstimatePocScopeInput` | `EstimatePocScopeOutput` containing weeks, roles, complexity points and assumptions | M1.3 implements versioned point mapping |

Weighted score calculation and Markdown rendering are domain/application services, not model-selected tools.
All twelve M1.2 tool contracts include `schema_version`, `correlation_id`,
`project_id` and `session_id`; they are framework-neutral Pydantic models and do
not execute tools. Each output is an exclusive success-or-error envelope: a success
requires its complete typed payload, while a failure carries `ToolError` without
fabricated success fields. `ToolError` contains a stable code, safe message,
retryability flag and JSON-only details.

The offline vertical-slice batch supplies framework-neutral implementations for
all six interfaces. Case retrieval is a transparent, version-controlled fixture
filter with fixed similarity values and `fixture:` source references; it is not
semantic search. The other services may calculate their individual typed output
fields from `AssessmentFacts`, but only `assess_project` recomputes the authoritative
six scores, weighted total, gate precedence and recommendation.

## 13. Case Knowledge Base Format

Each case is a reviewed UTF-8 Markdown file with YAML front matter:

```yaml
id: contract-review-assistant
title: 合約條款輔助審查
industry: [legal, professional-services]
problem: 大量 PDF 合約需要先標示可能的高風險條款
data_inputs: [pdf, scanned-pdf]
fit_conditions: [human-review-available, clause-policy-exists]
non_fit_conditions: [fully-automated-approval]
recommended_pattern: ocr-rag-rules-human-review
risk_flags: [confidential-data, legal-impact]
kpis: [review-time, risk-clause-recall, reviewer-override-rate]
human_review: required
source_urls: []
review_status: approved
```

The Markdown body explains context, workflow, fit/non-fit rationale, architecture pattern, risks and evaluation notes. Only `review_status: approved` cases enter the FAISS index. The SQLite row stores the content hash and FAISS vector IDs so stale indexes can be detected.

## 14. Scoring Framework — Single Source of Truth

| Dimension | Weight |
|---|---:|
| Business value／ROI clarity | 25% |
| Data readiness | 20% |
| Technical fit | 15% |
| Architecture controllability | 15% |
| Governance and privacy readiness | 15% |
| User adoption and change readiness | 10% |
| **Total** | **100%** |

Each dimension uses the 1–5 anchors defined in `deep-research-report.md`. Formula:

`weighted_points = Decimal(rating) / 5 × weight`, quantized to `0.01` with
`ROUND_HALF_UP`

`weighted_score = sum(weighted_points)`, quantized to a whole point with
`ROUND_HALF_UP`

Score-only labels:

- 75–100: 建議進行
- 55–74: 條件式建議
- 0–54: 暫不建議

The public M1.3 API is `assess_project(assessment_input: AssessmentInput) ->
Assessment`. It performs no I/O and uses the caller-supplied stable assessment ID
and UTC evaluation timestamp, so identical serialized input produces identical
serialized output. Tool-declared ratings are non-authoritative compatibility
fields; the engine recomputes all six ratings from `AssessmentFacts`.

## 15. Hard-gate Rules

Hard gates run before score interpretation and cannot be offset by ROI.

| Rule | Trigger | Disposition | Effect |
|---|---|---|---|
| HG-01 Unauthorized or autonomous use | No permission, lawful basis or accountable owner for required data/process; or autonomous final decisions／enterprise actions | `blocked` | No PoC recommendation; request authorization, constrain autonomy and obtain professional review |
| HG-02 High-impact final decision | Employment, medical, legal, credit or similar final decision without meaningful human review | `blocked` | Reject autonomous-final-decision scope |
| HG-03 High-impact assistive workflow | Same domains with documented human final decision and contest/review path | `assistive_only` | Cap at conditional; list mandatory controls |
| HG-04 Data cannot leave boundary | External endpoint conflicts with stated data boundary | `requires_controls` | Require approved local/private endpoint before proceeding |
| HG-05 Necessary controls missing | Required security, governance or audit controls are absent; sensitive/personal data additionally requires minimization, retention and access controls | `requires_controls` | Cap at conditional until controls exist |
| HG-06 Low data maturity | Data unavailable, mostly non-digital or no validation sample | `requires_controls` | Cap at conditional and output prerequisite work |
| HG-07 Financial final decision | Request asks the system to autonomously approve, price, lend or invest | `blocked` | MVP cannot perform or recommend autonomous financial decision |

Aggregate precedence: `blocked > assistive_only > requires_controls > pass`.

## 16. API Endpoints

| Method and path | Purpose | Success response |
|---|---|---|
| `GET /health` | Liveness and dependency mode | status, app version, fake/real model mode; no secrets |
| `POST /projects` | Create project | project record, `201` |
| `GET /projects/{project_id}` | Read project summary | project plus latest status |
| `POST /projects/{project_id}/interviews` | Start standard interview | session and first questions, `201` |
| `POST /projects/{project_id}/interviews/{session_id}/turns` | Submit one answer turn | accepted turn, normalized state, gaps and next questions |
| `GET /projects/{project_id}/interviews/{session_id}` | Resume interview | durable session, turns and state |
| `POST /projects/{project_id}/analysis` | Run retrieval, tools, gates and proposal assembly | assessment and validated proposal, `201` |
| `GET /projects/{project_id}/proposal` | Read latest proposal | `PocProposal` |
| `POST /projects/{project_id}/reports` | Render Markdown export | report metadata and content/path, `201` |
| `GET /projects/{project_id}/reports/{report_id}` | Read exported report | Markdown response or JSON envelope |

MVP endpoints are synchronous. Streaming, background jobs and authentication are Roadmap concerns.

## 17. Error Handling

All errors use:

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "safe user-facing message",
    "details": {},
    "correlation_id": "uuid"
  }
}
```

| Error | HTTP | Required behavior |
|---|---:|---|
| Pydantic input validation | 422 | Field-level safe details |
| Project/session/report not found | 404 | No data leakage across IDs |
| Invalid interview transition | 409 | Return current stage and allowed action |
| Incomplete information for analysis | 409 | Return missing fields and next questions |
| Hard-gate blocked | 200 assessment result | Business outcome, not transport failure |
| Model timeout/provider unavailable | 503 | Preserve accepted turn; safe retry allowed |
| Structured-output validation failure | 502 | Bounded retry, then fail without storing invalid proposal |
| FAISS index missing/stale | 503 | Explain reindex requirement; do not silently fabricate cases |
| Unexpected internal error | 500 | Correlation ID; no secrets or raw sensitive content |

## 18. Security and Privacy Constraints

- Secrets come only from environment variables or runtime secret facilities; `.env` is never committed.
- The public repository contains synthetic cases only.
- SQLite, FAISS, reports, traces and raw interview records are local ignored artifacts.
- Log field names and IDs, not full sensitive answers, unless an explicit safe debug mode is approved.
- Tool outputs are validated before entering Agent context.
- No MVP tool can mutate an enterprise system, send messages, approve decisions or perform financial actions.
- External model use requires an explicit data-boundary check; fake model is the safe default for tests.
- Markdown export escapes or neutralizes untrusted content where needed and never embeds secrets.
- This project flags governance issues; a qualified reviewer determines applicable law and compliance.

## 19. Commands

M1.1 establishes these executable standard-Python commands:

- Setup: `python -m pip install -e ".[dev]"`
- Smoke: `python -m ai_poc_planner`
- Test: `python -m pytest`
- Lint: `python -m ruff check .`

The API, UI and Docker commands remain TODO until their corresponding tasks create
the required files. Python 3.12 is the primary supported runtime.

## 20. Planned Project Structure

```text
src/ai_poc_planner/            Installable Python package
  domain/                      Pydantic contracts; later scoring and hard gates
  providers/                   Fake and future model provider adapters
  app/                         Planned FastAPI and application composition
  agent/                       Planned LangChain state, tools and prompts
  infrastructure/             Planned SQLite repositories and FAISS index
ui/                            Planned Streamlit application
case_library/                  Planned reviewed synthetic Markdown cases
tests/                         Unit, contract, integration and vertical-slice tests
docs/spec/                     Specification, plan and tasks
```

Folders are created only when their first approved implementation task needs them.

## 21. Code Style

- Python 3.12 primary target, confirmed by the M1.1 scaffold.
- Type annotations on public functions and Pydantic at boundaries.
- Small pure functions for scoring and hard gates.
- `snake_case` functions/fields, `PascalCase` classes, uppercase constants.
- Dependency injection for model, embeddings, repositories and clock/ID generation.
- No mutable class-level defaults; use `Field(default_factory=list)` where needed.

Documentation example:

```python
def weighted_points(rating: int, weight: int) -> float:
    """Convert a validated 1–5 rating into weighted percentage points."""
    if not 1 <= rating <= 5:
        raise ValueError("rating must be between 1 and 5")
    return rating / 5 * weight
```

## 22. Testing Strategy

- Unit: scoring, rubric mapping, hard gates, ROI math, KPI derivation and report renderer.
- Contract: every tool input/output and `PocProposal` validation.
- Repository: SQLite round trips and FAISS metadata/vector mapping in temporary paths.
- Trajectory: required tools called for each baseline case; forbidden tools absent.
- Multi-turn: fake model completes gaps and resumes from SQLite state.
- Vertical slice: API/application path completes create → interview → assess → report.
- Optional: export the same cases to LangSmith for offline comparison; never required for CI.

Minimum gates before implementation is considered complete:

- 100% Schema validity on baseline cases.
- 0 missed hard-gate invocation on hard-gate cases.
- 100% governance requirement for high-impact cases.
- No network access in fake-model test suite.

## 23. Boundaries

### Always

- Update the spec before changing a contract.
- Persist accepted user input before model calls.
- Run relevant pytest and lint checks before task completion.
- Keep hard gates independent from weighted scoring.
- Keep provider-specific code behind adapters.

### Ask First

- Add dependencies or change Python/runtime versions.
- Change database schema after implementation begins.
- Change weights, hard-gate precedence or report schema.
- Add external services, authentication, CI or deployment.
- Use real sensitive data or real model credentials.

### Never

- Commit secrets, local databases, FAISS indexes, reports, traces or interview data.
- Bypass hard gates because the weighted score is high.
- Give the Agent a tool that executes enterprise or financial actions in MVP.
- Replace professional legal, medical, employment, credit or financial decisions.
- Start multi-Agent, PostgreSQL or cloud work under an MVP task.

## 24. Acceptance Criteria

- AC-01 A fake-model run completes the full vertical slice without network.
- AC-02 Reloading the process resumes the interview from SQLite.
- AC-03 Missing critical information results in at most five targeted questions, not a proposal.
- AC-04 Similar cases include inspectable source references and SQLite metadata.
- AC-05 Six dimension ratings follow the rubric, weights total 100 and formula recomputes exactly.
- AC-06 A high ROI cannot change a `blocked` or `assistive_only` result.
- AC-07 Every baseline proposal validates against `PocProposal`.
- AC-08 Markdown report contains assumptions, evidence, score breakdown, hard gates, architecture, ROI/KPI, scope and next actions.
- AC-09 Docker development configuration reads secrets from environment and exposes no database port.
- AC-10 The repository contains no real secret, database, FAISS index, trace or user report.
- AC-11 README, PROJECT_LOG and TASKS reflect the implemented commands and status.

## 25. Open Questions for Human Review

- Which real OpenAI-compatible endpoint and model name should be the documented default after fake mode works?
- Should embeddings use the same endpoint as chat, or a separately configured adapter by default?
- Is Traditional Chinese-only output sufficient for MVP, or must report generation support English?
- Should exported Markdown be stored as a file, SQLite content, or both? The current proposal stores metadata plus a local file.
- Is LangSmith a Should item or entirely optional for the first public release?
