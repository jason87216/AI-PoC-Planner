from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

import ai_poc_planner.domain as domain
from ai_poc_planner.domain.enums import (
    DataBoundary,
    DecisionImpact,
    DigitizationLevel,
    EvidenceSourceType,
    GateDisposition,
    HumanReviewRequirement,
    InterviewRole,
    InterviewSessionStatus,
    InterviewStage,
    ProjectStatus,
    ReportFormat,
    ScoreDimension,
)
from ai_poc_planner.domain.models import (
    AnalysisProject,
    ArchitectureOption,
    ClarifyingQuestion,
    HardGateResult,
    InterviewTurn,
    ScoreDimensionResult,
    SimilarCase,
)
from ai_poc_planner.domain.tools import (
    AssessBusinessValueRoiAndKpisInput,
    AssessBusinessValueRoiAndKpisOutput,
    AssessDataReadinessInput,
    AssessDataReadinessOutput,
    AssessTechnicalFitAndArchitectureInput,
    AssessTechnicalFitAndArchitectureOutput,
    EstimatePocScopeInput,
    EstimatePocScopeOutput,
    EvaluateRiskAndHardGatesInput,
    EvaluateRiskAndHardGatesOutput,
    KpiProposal,
    RetrieveSimilarCasesInput,
    RetrieveSimilarCasesOutput,
    ToolError,
)
from ai_poc_planner.domain.workflow import (
    AgentState,
    Assessment,
    AssessmentInput,
    CaseMetadata,
    ConversationStateSnapshot,
    EvidenceReference,
    InterviewSession,
    PocProposalRecord,
    ReportExport,
)
from ai_poc_planner.providers.base import ProviderRequest
from ai_poc_planner.providers.fake import FakeModelProvider

NOW = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)
PROJECT_ID = UUID("00000000-0000-0000-0000-000000000101")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000201")
ASSESSMENT_ID = UUID("00000000-0000-0000-0000-000000000301")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000401")


def _project() -> AnalysisProject:
    return AnalysisProject(
        id=PROJECT_ID,
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.INTERVIEWING,
        created_at=NOW,
        updated_at=NOW,
    )


def _turn(sequence: int, *, session_id: UUID = SESSION_ID) -> InterviewTurn:
    return InterviewTurn(
        id=UUID(int=500 + sequence),
        session_id=session_id,
        sequence=sequence,
        role=InterviewRole.USER,
        content=f"第 {sequence} 個固定回答",
        normalized_answers={"sequence": sequence},
        created_at=NOW,
    )


def _scores() -> list[ScoreDimensionResult]:
    values = [
        (ScoreDimension.BUSINESS_VALUE, 4, 25, 20.0),
        (ScoreDimension.DATA_READINESS, 3, 20, 12.0),
        (ScoreDimension.TECHNICAL_FIT, 4, 15, 12.0),
        (ScoreDimension.ARCHITECTURE_CONTROLLABILITY, 4, 15, 12.0),
        (ScoreDimension.GOVERNANCE_READINESS, 3, 15, 9.0),
        (ScoreDimension.USER_ADOPTION, 4, 10, 8.0),
    ]
    return [
        ScoreDimensionResult(
            dimension=dimension,
            rating=rating,
            weight=weight,
            weighted_points=points,
            rationale="固定 contract fixture。",
            evidence_refs=["interview:baseline"],
        )
        for dimension, rating, weight, points in values
    ]


def _gate() -> HardGateResult:
    return HardGateResult(
        rule_id="HG-BASELINE",
        disposition=GateDisposition.PASS,
        reason="未觸發 hard gate。",
        required_controls=[],
        human_review_required=False,
    )


def test_interview_session_accepts_consistent_ordered_turns() -> None:
    session = InterviewSession(
        id=SESSION_ID,
        project_id=PROJECT_ID,
        status=InterviewSessionStatus.ACTIVE,
        current_stage=InterviewStage.DATA,
        state_version=2,
        turns=[_turn(1), _turn(2)],
        created_at=NOW,
        updated_at=NOW,
    )

    assert session.project_id == PROJECT_ID
    assert [turn.sequence for turn in session.turns] == [1, 2]


def test_interview_session_rejects_turn_from_another_session() -> None:
    with pytest.raises(ValidationError, match="turn session_id"):
        InterviewSession(
            id=SESSION_ID,
            project_id=PROJECT_ID,
            status=InterviewSessionStatus.ACTIVE,
            current_stage=InterviewStage.CONTEXT,
            state_version=1,
            turns=[_turn(1, session_id=UUID(int=999))],
            created_at=NOW,
            updated_at=NOW,
        )


def test_interview_session_rejects_non_contiguous_turn_sequence() -> None:
    with pytest.raises(ValidationError, match="contiguous"):
        InterviewSession(
            id=SESSION_ID,
            project_id=PROJECT_ID,
            status=InterviewSessionStatus.ACTIVE,
            current_stage=InterviewStage.VALUE,
            state_version=2,
            turns=[_turn(1), _turn(3)],
            created_at=NOW,
            updated_at=NOW,
        )


def test_assessment_stores_all_dimensions_and_gate_results() -> None:
    assessment = Assessment(
        schema_version="1.0",
        id=ASSESSMENT_ID,
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        rule_version="1.0",
        scores=_scores(),
        weighted_score=73,
        hard_gates=[_gate()],
        gate_disposition=GateDisposition.PASS,
        recommendation="條件式建議",
        matched_case_ids=["case-001"],
        evidence_refs=["interview:baseline"],
        rationale="固定 assessment contract。",
        created_at=NOW,
    )

    assert len(assessment.scores) == 6
    assert assessment.hard_gates[0].rule_id == "HG-BASELINE"


def test_assessment_rejects_missing_score_dimension() -> None:
    with pytest.raises(ValidationError, match="each dimension exactly once"):
        Assessment(
            schema_version="1.0",
            id=ASSESSMENT_ID,
            project_id=PROJECT_ID,
            session_id=SESSION_ID,
            rule_version="1.0",
            scores=_scores()[:-1],
            weighted_score=65,
            hard_gates=[_gate()],
            gate_disposition=GateDisposition.PASS,
            recommendation="暫不建議",
            matched_case_ids=[],
            evidence_refs=[],
            rationale="缺少一個維度。",
            created_at=NOW,
        )


def test_score_contract_rejects_wrong_normative_weight() -> None:
    with pytest.raises(ValidationError, match="must be 25"):
        ScoreDimensionResult(
            dimension=ScoreDimension.BUSINESS_VALUE,
            rating=4,
            weight=20,
            weighted_points=16,
            rationale="錯誤權重。",
            evidence_refs=[],
        )


def test_assessment_contract_does_not_calculate_weighted_score() -> None:
    assessment = Assessment(
        schema_version="1.0",
        id=ASSESSMENT_ID,
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        rule_version="1.0",
        scores=_scores(),
        weighted_score=0,
        hard_gates=[_gate()],
        gate_disposition=GateDisposition.PASS,
        recommendation="暫不建議",
        matched_case_ids=[],
        evidence_refs=[],
        rationale="M1.3 尚未計算，contract 只驗證合法範圍。",
        created_at=NOW,
    )

    assert assessment.weighted_score == 0


def test_proposal_contract_does_not_decide_recommendation() -> None:
    proposal = FakeModelProvider().generate(ProviderRequest(project=_project()))
    payload = proposal.model_dump(mode="json")
    payload["gate_disposition"] = "blocked"
    payload["recommendation"] = "建議進行"

    validated = type(proposal).model_validate(payload)

    assert validated.recommendation.value == "建議進行"


def test_assessment_input_and_evidence_round_trip() -> None:
    assessment_input = AssessmentInput(
        schema_version="1.0",
        project_id=PROJECT_ID,
        session_id=SESSION_ID,
        known_information={"baseline": {"minutes": 10}},
        evidence=[
            EvidenceReference(
                id=UUID(int=903),
                source_type=EvidenceSourceType.INTERVIEW,
                source_ref="turn:1",
                label="Baseline answer",
                metadata={"field": "baseline.minutes"},
            )
        ],
    )

    restored = AssessmentInput.model_validate_json(
        assessment_input.model_dump_json()
    )

    assert restored == assessment_input


def test_persistence_records_round_trip_through_json() -> None:
    proposal = FakeModelProvider().generate(ProviderRequest(project=_project()))
    proposal_record = PocProposalRecord(
        id=PROPOSAL_ID,
        project_id=PROJECT_ID,
        assessment_id=ASSESSMENT_ID,
        schema_version="1.0",
        payload=proposal,
        created_at=NOW,
    )
    case = CaseMetadata(
        id=UUID(int=701),
        title="合成客服案例",
        industry=["retail"],
        problem="客服查找產品知識耗時。",
        fit_conditions=["approved-knowledge"],
        non_fit_conditions=["autonomous-final-decision"],
        pattern="local-rag-human-review",
        risk_flags=["customer-data"],
        kpis=["lookup-time"],
        human_review=HumanReviewRequirement.REQUIRED,
        source_path="case_library/customer-support.md",
        content_hash="a" * 64,
        created_at=NOW,
        updated_at=NOW,
    )
    report = ReportExport(
        id=UUID(int=801),
        project_id=PROJECT_ID,
        proposal_id=PROPOSAL_ID,
        format=ReportFormat.MARKDOWN,
        content_hash="b" * 64,
        local_path="reports/proposal.md",
        created_at=NOW,
    )

    assert (
        PocProposalRecord.model_validate_json(proposal_record.model_dump_json())
        == proposal_record
    )
    assert CaseMetadata.model_validate_json(case.model_dump_json()) == case
    assert ReportExport.model_validate_json(report.model_dump_json()) == report


def test_persistence_datetime_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        ConversationStateSnapshot(
            schema_version="1.0",
            session_id=SESSION_ID,
            version=1,
            known_fields={},
            missing_fields=[],
            contradictions=[],
            created_at=datetime(2026, 7, 19, 12, 0),
        )


def test_schema_version_rejects_non_semantic_format() -> None:
    with pytest.raises(ValidationError):
        ConversationStateSnapshot(
            schema_version="version-one",
            session_id=SESSION_ID,
            version=1,
            known_fields={},
            missing_fields=[],
            contradictions=[],
            created_at=NOW,
        )


def _agent_state(**overrides: object) -> AgentState:
    values: dict[str, object] = {
        "schema_version": "1.0",
        "project_id": PROJECT_ID,
        "session_id": SESSION_ID,
        "session_project_id": PROJECT_ID,
        "workflow_stage": ProjectStatus.CLARIFICATION_REQUIRED,
        "interview_stage": InterviewStage.DATA,
        "known_fields": {
            "data": {
                "sources": ["knowledge-base", {"format": "markdown"}],
                "authorized": True,
            }
        },
        "missing_fields": ["data.owner"],
        "contradictions": [],
        "questions_asked": ["誰負責核准知識內容？"],
        "clarifying_questions": [
            ClarifyingQuestion(
                field="data.owner",
                question="誰負責核准知識內容？",
                reason="需要可問責的資料擁有者。",
                priority=1,
            )
        ],
        "similar_case_ids": [],
        "evidence_refs": [UUID(int=904)],
        "tool_results": {},
    }
    values.update(overrides)
    return AgentState.model_validate(values)


def test_agent_state_round_trips_with_explicit_question_types() -> None:
    state = _agent_state()

    restored = AgentState.model_validate_json(state.model_dump_json())

    assert restored == state
    assert isinstance(restored.clarifying_questions[0], ClarifyingQuestion)


def test_agent_state_rejects_session_project_mismatch() -> None:
    with pytest.raises(ValidationError, match="session project ID"):
        _agent_state(session_project_id=UUID(int=999))


def test_agent_state_rejects_duplicate_evidence_references() -> None:
    with pytest.raises(ValidationError, match="evidence_refs must not contain"):
        _agent_state(evidence_refs=[UUID(int=904), UUID(int=904)])


def test_agent_state_rejects_duplicate_clarifying_question_fields() -> None:
    question = ClarifyingQuestion(
        field="data.owner",
        question="Who owns this data?",
        reason="An accountable owner is required.",
        priority=1,
    )

    with pytest.raises(ValidationError, match="clarifying question fields"):
        _agent_state(clarifying_questions=[question, question])


def test_agent_state_rejects_duplicate_clarifying_question_text() -> None:
    questions = [
        ClarifyingQuestion(
            field=field,
            question="Who owns this data?",
            reason="An accountable owner is required.",
            priority=priority,
        )
        for field, priority in (("data.owner", 1), ("data.approver", 2))
    ]

    with pytest.raises(ValidationError, match="clarifying question text"):
        _agent_state(clarifying_questions=questions)


def test_agent_state_rejects_unknown_workflow_stage() -> None:
    with pytest.raises(ValidationError):
        _agent_state(workflow_stage="invented-stage")


@pytest.mark.parametrize(
    ("stage", "expected_message"),
    [
        (ProjectStatus.ASSESSED, "requires assessment_id"),
        (ProjectStatus.PROPOSAL_GENERATED, "requires assessment_id"),
        (ProjectStatus.COMPLETE, "requires assessment_id"),
    ],
)
def test_agent_state_rejects_missing_assessment_reference(
    stage: ProjectStatus, expected_message: str
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        _agent_state(
            workflow_stage=stage,
            interview_stage=InterviewStage.COMPLETE,
        )


def test_agent_state_rejects_missing_proposal_reference() -> None:
    with pytest.raises(ValidationError, match="requires proposal_id"):
        _agent_state(
            workflow_stage=ProjectStatus.PROPOSAL_GENERATED,
            interview_stage=InterviewStage.COMPLETE,
            assessment_id=ASSESSMENT_ID,
        )


def test_agent_state_rejects_completed_interview_with_active_workflow() -> None:
    with pytest.raises(ValidationError, match="interview stage and workflow stage"):
        _agent_state(
            workflow_stage=ProjectStatus.INTERVIEWING,
            interview_stage=InterviewStage.COMPLETE,
        )


def test_recursive_json_value_accepts_nested_lists_and_objects() -> None:
    snapshot = ConversationStateSnapshot(
        schema_version="1.0",
        session_id=SESSION_ID,
        version=1,
        known_fields={
            "nested": [1, True, None, {"levels": ["one", {"two": 2.5}]}]
        },
        missing_fields=[],
        contradictions=[],
        created_at=NOW,
    )

    assert ConversationStateSnapshot.model_validate_json(
        snapshot.model_dump_json()
    ) == snapshot


@pytest.mark.parametrize("invalid", [object(), ("tuple",), {"set"}])
def test_recursive_json_value_rejects_unsupported_python_objects(
    invalid: object,
) -> None:
    with pytest.raises(ValidationError, match="JSON-compatible"):
        ConversationStateSnapshot(
            schema_version="1.0",
            session_id=SESSION_ID,
            version=1,
            known_fields={"invalid": invalid},
            missing_fields=[],
            contradictions=[],
            created_at=NOW,
        )


def test_fixed_agent_state_serialization_is_deterministic() -> None:
    first = _agent_state().model_dump_json()
    second = _agent_state().model_dump_json()

    assert first == second


def _tool_context() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "correlation_id": UUID(int=901),
        "project_id": PROJECT_ID,
        "session_id": SESSION_ID,
    }


def _tool_inputs() -> list[object]:
    context = _tool_context()
    return [
        RetrieveSimilarCasesInput(
            **context,
            normalized_problem="客服需要檢索已核准的產品知識。",
            industries=["retail"],
            data_filters={"formats": ["markdown", "pdf"]},
            risk_filters={"exclude": ["autonomous-decision"]},
            top_k=3,
        ),
        AssessDataReadinessInput(
            **context,
            data_sources=["approved-knowledge-base"],
            access_confirmed=True,
            digitization=DigitizationLevel.COMPLETE,
            quality_notes=["owner identified"],
            labels_available=None,
            validation_sample_available=True,
        ),
        AssessTechnicalFitAndArchitectureInput(
            **context,
            task_pattern="retrieval-assistance",
            required_reasoning=["source selection"],
            required_tools=["local retrieval"],
            integrations=[],
            deployment_constraints=["local-only"],
        ),
        EvaluateRiskAndHardGatesInput(
            **context,
            domain="customer-support",
            decision_impact=DecisionImpact.LOW,
            personal_data=False,
            sensitive_data=False,
            data_boundary=DataBoundary.LOCAL_ONLY,
            human_review_available=True,
            authorization_confirmed=True,
        ),
        AssessBusinessValueRoiAndKpisInput(
            **context,
            owner="客服主管",
            baseline_description="平均查找時間十分鐘。",
            monthly_volume=1000,
            current_cost=None,
            current_time_minutes=10,
            expected_change="將平均查找時間降至五分鐘。",
            adoption_evidence=["客服主管願意安排試用"],
        ),
        EstimatePocScopeInput(
            **context,
            requires_ocr=False,
            integration_count=0,
            requires_review_ui=True,
            evaluation_data_available=True,
            handles_sensitive_data=False,
            department_count=1,
        ),
    ]


def _tool_outputs() -> list[object]:
    context = _tool_context()
    scores = {score.dimension: score for score in _scores()}
    return [
        RetrieveSimilarCasesOutput(
            **context,
            cases=[
                SimilarCase(
                    case_id="case-001",
                    title="合成檢索案例",
                    similarity=0.8,
                    fit_summary="適合人工覆核的知識檢索。",
                    source_ref="case_library/case-001.md",
                )
            ],
            evidence=[
                EvidenceReference(
                    id=UUID(int=902),
                    source_type=EvidenceSourceType.CASE,
                    source_ref="case_library/case-001.md",
                    label="合成檢索案例",
                )
            ],
        ),
        AssessDataReadinessOutput(
            **context,
            score=scores[ScoreDimension.DATA_READINESS],
            gaps=["需確認更新頻率"],
            prerequisites=["建立驗證問題集"],
            rationale="資料可取得但仍需驗證。",
        ),
        AssessTechnicalFitAndArchitectureOutput(
            **context,
            technical_fit=scores[ScoreDimension.TECHNICAL_FIT],
            architecture_controllability=scores[
                ScoreDimension.ARCHITECTURE_CONTROLLABILITY
            ],
            architecture_options=[
                ArchitectureOption(
                    name="local retrieval",
                    summary="本機索引搭配人工覆核。",
                    deployment="local",
                    components=["retrieval", "review"],
                    assumptions=[],
                )
            ],
            rationale="可由受控本機元件組成。",
        ),
        EvaluateRiskAndHardGatesOutput(
            **context,
            rule_version="1.0",
            hard_gates=[_gate()],
            gate_disposition=GateDisposition.PASS,
            governance_readiness=scores[ScoreDimension.GOVERNANCE_READINESS],
        ),
        AssessBusinessValueRoiAndKpisOutput(
            **context,
            business_value=scores[ScoreDimension.BUSINESS_VALUE],
            user_adoption=scores[ScoreDimension.USER_ADOPTION],
            roi_assumptions=["每月處理量維持 1000 件"],
            kpi_proposals=[
                KpiProposal(
                    name="average lookup time",
                    unit="minutes",
                    baseline=10,
                    target=5,
                    direction="decrease",
                )
            ],
            rationale="具有可量測時間基準。",
        ),
        EstimatePocScopeOutput(
            **context,
            estimated_weeks=2,
            roles=["AI／Solution Engineer", "客服流程負責人"],
            complexity_points=3,
            assumptions=["不含企業系統整合"],
        ),
    ]


@pytest.mark.parametrize("tool_input", _tool_inputs())
def test_all_six_tool_input_contracts_can_be_created(tool_input: object) -> None:
    assert tool_input is not None


@pytest.mark.parametrize("tool_output", _tool_outputs())
def test_all_six_tool_output_contracts_can_be_created(tool_output: object) -> None:
    assert tool_output is not None


@pytest.mark.parametrize("tool_contract", [*_tool_inputs(), *_tool_outputs()])
def test_tool_contracts_round_trip_through_json(tool_contract: object) -> None:
    restored = type(tool_contract).model_validate_json(tool_contract.model_dump_json())

    assert restored == tool_contract


@pytest.mark.parametrize("tool_input", _tool_inputs())
def test_tool_input_rejects_missing_project_reference(tool_input: object) -> None:
    payload = tool_input.model_dump(mode="json", exclude={"project_id"})

    with pytest.raises(ValidationError) as error:
        type(tool_input).model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("project_id",)


@pytest.mark.parametrize("tool_output", _tool_outputs())
def test_tool_output_rejects_missing_project_reference(tool_output: object) -> None:
    payload = tool_output.model_dump(mode="json", exclude={"project_id"})

    with pytest.raises(ValidationError) as error:
        type(tool_output).model_validate(payload)

    assert error.value.errors()[0]["loc"] == ("project_id",)


def test_tool_contract_rejects_duplicate_collection_values() -> None:
    with pytest.raises(ValidationError, match="data_sources must not contain"):
        AssessDataReadinessInput(
            **_tool_context(),
            data_sources=["knowledge-base", "knowledge-base"],
            access_confirmed=True,
            digitization=DigitizationLevel.COMPLETE,
            quality_notes=[],
            labels_available=None,
            validation_sample_available=True,
        )


def test_tool_error_is_small_serializable_and_framework_neutral() -> None:
    error = ToolError(
        code="index_unavailable",
        message="Local case index is unavailable.",
        retryable=True,
        details={"action": "reindex"},
    )

    assert ToolError.model_validate_json(error.model_dump_json()) == error


def _tool_failure_outputs() -> list[object]:
    error = ToolError(
        code="tool_unavailable",
        message="The local tool is unavailable.",
        retryable=True,
        details={"action": "retry"},
    )
    context = _tool_context()
    return [
        output_type(**context, error=error)
        for output_type in (
            RetrieveSimilarCasesOutput,
            AssessDataReadinessOutput,
            AssessTechnicalFitAndArchitectureOutput,
            EvaluateRiskAndHardGatesOutput,
            AssessBusinessValueRoiAndKpisOutput,
            EstimatePocScopeOutput,
        )
    ]


@pytest.mark.parametrize("tool_output", _tool_failure_outputs())
def test_tool_failure_output_needs_no_success_payload_and_round_trips(
    tool_output: object,
) -> None:
    restored = type(tool_output).model_validate_json(tool_output.model_dump_json())

    assert restored == tool_output
    assert restored.error is not None


@pytest.mark.parametrize("tool_output", _tool_outputs())
def test_tool_output_rejects_error_together_with_success_payload(
    tool_output: object,
) -> None:
    payload = tool_output.model_dump(mode="json")
    payload["error"] = {
        "code": "contradictory_result",
        "message": "A result cannot be successful and failed.",
        "retryable": False,
        "details": {},
    }

    with pytest.raises(ValidationError, match="must not include success payload"):
        type(tool_output).model_validate(payload)


def test_score_and_gate_collections_reject_empty_or_duplicate_values() -> None:
    with pytest.raises(ValidationError, match="evidence_refs"):
        ScoreDimensionResult(
            dimension=ScoreDimension.DATA_READINESS,
            rating=3,
            weight=20,
            weighted_points=12,
            rationale="Evidence reference is invalid.",
            evidence_refs=["", ""],
        )

    with pytest.raises(ValidationError, match="required_controls"):
        HardGateResult(
            rule_id="HG-04",
            disposition=GateDisposition.REQUIRES_CONTROLS,
            reason="Boundary control is required.",
            required_controls=["private endpoint", "private endpoint"],
            human_review_required=True,
        )


def test_m12_contracts_are_available_from_domain_public_interface() -> None:
    expected_names = {
        "AgentState",
        "Assessment",
        "AssessmentInput",
        "CaseMetadata",
        "ConversationStateSnapshot",
        "EvidenceReference",
        "InterviewSession",
        "PocProposalRecord",
        "ReportExport",
        "RetrieveSimilarCasesInput",
        "RetrieveSimilarCasesOutput",
        "AssessDataReadinessInput",
        "AssessDataReadinessOutput",
        "AssessTechnicalFitAndArchitectureInput",
        "AssessTechnicalFitAndArchitectureOutput",
        "EvaluateRiskAndHardGatesInput",
        "EvaluateRiskAndHardGatesOutput",
        "AssessBusinessValueRoiAndKpisInput",
        "AssessBusinessValueRoiAndKpisOutput",
        "EstimatePocScopeInput",
        "EstimatePocScopeOutput",
        "ToolError",
    }

    assert expected_names <= set(domain.__all__)
