"""Framework-neutral Phase 3 discovery and interview contracts.

Only user-visible conversation and validated structured facts are represented
here.  Prompts, reasoning traces, raw provider responses, secrets, and tool
metadata intentionally have no place in these contracts.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field, model_validator

from ai_poc_planner.domain.enums import (
    AvailableDataStatus,
    DiscoverySessionStatus,
    FactStatus,
    InterviewAnswerStatus,
)
from ai_poc_planner.domain.models import (
    ContractModel,
    JSONValue,
    NonEmptyStr,
    UtcDateTime,
)


class InitialBrief(ContractModel):
    project_name: NonEmptyStr
    current_workflow_problem: NonEmptyStr
    desired_outcome: NonEmptyStr
    available_data: NonEmptyStr
    users_and_owners: NonEmptyStr | None = None
    known_constraints: NonEmptyStr | None = None


class NormalizedInitialBrief(InitialBrief):
    available_data_status: AvailableDataStatus


class DiscoverySession(ContractModel):
    id: UUID
    version_id: UUID
    brief_message_id: UUID
    latest_understanding_message_id: UUID | None = None
    understanding_revision: int = Field(default=0, ge=0)
    status: DiscoverySessionStatus
    current_round: int = Field(ge=0, le=3)
    understanding_confirmed_at: UtcDateTime | None = None
    completed_at: UtcDateTime | None = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> DiscoverySession:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")
        if self.completed_at is not None and self.completed_at < self.created_at:
            raise ValueError("completed_at must not be earlier than created_at")
        return self


class InterviewQuestion(ContractModel):
    id: UUID
    session_id: UUID
    version_id: UUID
    round_number: int = Field(ge=1, le=3)
    position: int = Field(ge=1, le=3)
    visible_message_id: UUID
    fact_key: NonEmptyStr
    question: NonEmptyStr
    why_it_matters: NonEmptyStr
    affected_judgement: NonEmptyStr
    example: NonEmptyStr
    answer_message_id: UUID | None = None
    created_at: UtcDateTime
    answered_at: UtcDateTime | None = None


class ProposedAssumption(ContractModel):
    fact_key: NonEmptyStr
    value: JSONValue
    rationale: NonEmptyStr
    source_fact_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def source_ids_are_unique(self) -> ProposedAssumption:
        if len(self.source_fact_ids) != len(set(self.source_fact_ids)):
            raise ValueError("source_fact_ids must not contain duplicates")
        return self


class DetectedAmbiguity(ContractModel):
    description: NonEmptyStr
    related_fact_ids: list[UUID] = Field(min_length=1)


class RequirementUnderstanding(ContractModel):
    concise_requirement_summary: NonEmptyStr
    current_workflow_understanding: NonEmptyStr
    desired_outcome_understanding: NonEmptyStr
    available_data_understanding: NonEmptyStr
    users_and_owners_understanding: NonEmptyStr | None = None
    known_constraints_understanding: NonEmptyStr | None = None
    proposed_assumptions: list[ProposedAssumption] = Field(default_factory=list)
    detected_contradictions_or_ambiguities: list[DetectedAmbiguity] = Field(
        default_factory=list
    )


class InterviewQuestionOutput(ContractModel):
    fact_key: NonEmptyStr
    question: NonEmptyStr
    why_it_matters: NonEmptyStr
    affected_judgement: NonEmptyStr
    example: NonEmptyStr

    @model_validator(mode="after")
    def does_not_request_internal_provider_information(self) -> InterviewQuestionOutput:
        forbidden = (
            "api key",
            "authorization",
            "system prompt",
            "chain of thought",
            "provider",
        )
        text = " ".join((self.question, self.why_it_matters)).casefold()
        if any(item in text for item in forbidden):
            raise ValueError("interview questions cannot request provider internals")
        return self


class InterviewRoundOutput(ContractModel):
    interview_complete: bool
    questions: list[InterviewQuestionOutput] = Field(max_length=3)

    @model_validator(mode="after")
    def completion_matches_questions(self) -> InterviewRoundOutput:
        if self.interview_complete and self.questions:
            raise ValueError("completed interview output must not include questions")
        if not self.interview_complete and not self.questions:
            raise ValueError("active interview output requires at least one question")
        return self


class InterviewAnswer(ContractModel):
    question_id: UUID
    answer_status: InterviewAnswerStatus
    answer: NonEmptyStr | None = None

    @model_validator(mode="after")
    def answer_matches_status(self) -> InterviewAnswer:
        if self.answer_status is InterviewAnswerStatus.ANSWERED and self.answer is None:
            raise ValueError("answered status requires answer")
        if (
            self.answer_status is not InterviewAnswerStatus.ANSWERED
            and self.answer is not None
        ):
            raise ValueError("unknown and missing answers require null answer")
        return self


class AdditionalFact(ContractModel):
    fact_key: NonEmptyStr
    status: FactStatus
    value: JSONValue

    @model_validator(mode="after")
    def is_user_recordable_fact(self) -> AdditionalFact:
        if self.status is FactStatus.ASSUMPTION:
            raise ValueError("user additions cannot create assumptions")
        if (
            self.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
            and self.value is not None
        ):
            raise ValueError("unknown and missing facts require null value")
        if self.status is FactStatus.CONFIRMED and self.value is None:
            raise ValueError("confirmed facts require a value")
        return self


class FactCorrectionCommand(ContractModel):
    target_fact_id: UUID
    status: FactStatus
    value: JSONValue
    correction_reason: NonEmptyStr

    @model_validator(mode="after")
    def is_valid_correction(self) -> FactCorrectionCommand:
        if self.status is FactStatus.ASSUMPTION:
            raise ValueError("correction cannot create an assumption")
        if self.status in {FactStatus.UNKNOWN, FactStatus.MISSING}:
            if self.value is not None:
                raise ValueError("unknown and missing facts require null value")
        elif self.value is None:
            raise ValueError("confirmed facts require a value")
        return self


class UnderstandingCorrectionSubmission(ContractModel):
    corrections: list[FactCorrectionCommand] = Field(default_factory=list)
    additional_facts: list[AdditionalFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def has_changes(self) -> UnderstandingCorrectionSubmission:
        if not self.corrections and not self.additional_facts:
            raise ValueError("corrections require at least one change")
        return self


class InterviewRoundAnswerSubmission(ContractModel):
    answers: list[InterviewAnswer] = Field(min_length=1)
    additional_facts: list[AdditionalFact] = Field(default_factory=list)
    corrections: list[FactCorrectionCommand] = Field(default_factory=list)

    @model_validator(mode="after")
    def question_ids_are_unique(self) -> InterviewRoundAnswerSubmission:
        ids = [answer.question_id for answer in self.answers]
        if len(ids) != len(set(ids)):
            raise ValueError("answers must not repeat question IDs")
        return self
