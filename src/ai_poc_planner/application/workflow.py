"""Complete in-memory offline planning workflow."""

from __future__ import annotations

from pydantic import ValidationError

from ai_poc_planner.application.contracts import (
    OfflinePlanningRequest,
    OfflinePlanningResult,
)
from ai_poc_planner.application.proposal import (
    ProposalGenerationError,
    generate_proposal,
)
from ai_poc_planner.application.report import (
    render_markdown_report,
    write_markdown_report,
)
from ai_poc_planner.application.tool_services import (
    TOOL_NAMES,
    run_assessment_tools,
)
from ai_poc_planner.assessment.engine import AssessmentError, assess_project
from ai_poc_planner.domain.models import ClarifyingQuestion
from ai_poc_planner.domain.workflow import AssessmentInput
from ai_poc_planner.providers.base import (
    ModelProvider,
    PreparationStatus,
    ProviderError,
    ProviderPreparation,
    ProviderRequest,
)
from ai_poc_planner.providers.fake import FakeModelProvider


class PlanningError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ProviderWorkflowError(PlanningError):
    pass


class ClarificationRequiredError(PlanningError):
    def __init__(self, questions: list[ClarifyingQuestion]) -> None:
        super().__init__(
            "clarification_required",
            "interview information is incomplete; clarification is required",
        )
        self.questions = tuple(questions)


class ToolWorkflowError(PlanningError):
    pass


class AssessmentWorkflowError(PlanningError):
    pass


class ProposalWorkflowError(PlanningError):
    pass


def run_offline_planning(
    request: OfflinePlanningRequest,
    *,
    provider: ModelProvider | None = None,
) -> OfflinePlanningResult:
    """Run the deterministic in-memory project-to-Markdown vertical slice."""
    selected_provider = provider if provider is not None else FakeModelProvider()
    provider_request = ProviderRequest(
        project=request.project,
        session_id=request.session_id,
        interview_answers=request.interview_answers,
        evidence=request.evidence,
    )
    try:
        raw_preparation = selected_provider.prepare_assessment(provider_request)
        preparation = ProviderPreparation.model_validate(raw_preparation)
    except ProviderError as error:
        raise ProviderWorkflowError("provider_error", str(error)) from error
    except ValidationError as error:
        raise ProviderWorkflowError(
            "provider_output_invalid",
            "provider returned invalid structured output",
        ) from error

    if preparation.status is PreparationStatus.CLARIFICATION_REQUIRED:
        raise ClarificationRequiredError(preparation.clarifying_questions)
    assert preparation.facts is not None
    assert preparation.tool_inputs is not None

    try:
        outputs = run_assessment_tools(
            preparation.tool_inputs,
            preparation.facts,
            fail_tool=request.fail_tool,
        )
    except ValueError as error:
        raise ToolWorkflowError("invalid_tool_request", str(error)) from error
    for tool_name in TOOL_NAMES:
        output = getattr(outputs, tool_name)
        if output is not None and output.error is not None:
            raise ToolWorkflowError(
                "assessment_tool_error",
                f"assessment tool failed: {tool_name} ({output.error.code})",
            )

    try:
        assessment = assess_project(
            AssessmentInput(
                schema_version="1.0",
                project_id=request.project.id,
                session_id=request.session_id,
                assessment_id=request.assessment_id,
                evaluated_at=request.evaluated_at,
                known_information=request.interview_answers,
                facts=preparation.facts,
                tool_outputs=outputs,
                evidence=request.evidence,
            )
        )
    except AssessmentError as error:
        raise AssessmentWorkflowError(error.code, str(error)) from error

    retrieval = outputs.retrieve_similar_cases
    assert retrieval is not None
    retrieval_evidence = retrieval.evidence or []
    all_evidence = [*request.evidence, *retrieval_evidence]
    try:
        proposal = generate_proposal(
            project=request.project,
            interview_answers=request.interview_answers,
            assessment=assessment,
            tool_outputs=outputs,
            evidence=request.evidence,
        )
    except ProposalGenerationError as error:
        raise ProposalWorkflowError(error.code, str(error)) from error

    markdown = render_markdown_report(
        project=request.project,
        interview_answers=request.interview_answers,
        assessment=assessment,
        proposal=proposal,
        evidence=all_evidence,
    )
    report_path = (
        write_markdown_report(markdown, request.output_path)
        if request.output_path is not None
        else None
    )
    return OfflinePlanningResult(
        project=request.project,
        assessment=assessment,
        proposal=proposal,
        markdown=markdown,
        report_path=report_path,
    )
