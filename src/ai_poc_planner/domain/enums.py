"""Finite domain states defined by the version 1 specification."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    INTERVIEWING = "interviewing"
    CLARIFICATION_REQUIRED = "clarification_required"
    READY_FOR_ASSESSMENT = "ready_for_assessment"
    ASSESSED = "assessed"
    PROPOSAL_GENERATED = "proposal_generated"
    COMPLETE = "complete"
    FAILED = "failed"


class PlanningRunStatus(StrEnum):
    CREATED = "created"
    CLARIFICATION_REQUIRED = "clarification_required"
    COMPLETED = "completed"
    FAILED = "failed"


class InterviewSessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class InterviewStage(StrEnum):
    CONTEXT = "context"
    DATA = "data"
    VALUE = "value"
    GOVERNANCE = "governance"
    REVIEW = "review"
    COMPLETE = "complete"


class InterviewRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ScoreDimension(StrEnum):
    BUSINESS_VALUE = "business_value"
    DATA_READINESS = "data_readiness"
    TECHNICAL_FIT = "technical_fit"
    ARCHITECTURE_CONTROLLABILITY = "architecture_controllability"
    GOVERNANCE_READINESS = "governance_readiness"
    USER_ADOPTION = "user_adoption"


class GateDisposition(StrEnum):
    PASS = "pass"
    REQUIRES_CONTROLS = "requires_controls"
    ASSISTIVE_ONLY = "assistive_only"
    BLOCKED = "blocked"


class Recommendation(StrEnum):
    RECOMMENDED = "建議進行"
    CONDITIONAL = "條件式建議"
    NOT_RECOMMENDED = "暫不建議"


class HumanReviewRequirement(StrEnum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    NOT_REQUIRED = "not_required"


class ReportFormat(StrEnum):
    MARKDOWN = "markdown"


class EvidenceSourceType(StrEnum):
    INTERVIEW = "interview"
    CASE = "case"
    TOOL = "tool"
    USER_INPUT = "user_input"


class DigitizationLevel(StrEnum):
    NONE = "none"
    PARTIAL = "partial"
    MOSTLY = "mostly"
    COMPLETE = "complete"


class DecisionImpact(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataBoundary(StrEnum):
    LOCAL_ONLY = "local_only"
    PRIVATE_ENDPOINT = "private_endpoint"
    EXTERNAL_ALLOWED = "external_allowed"


class HighImpactDomain(StrEnum):
    NONE = "none"
    EMPLOYMENT = "employment"
    MEDICAL = "medical"
    LEGAL = "legal"
    CREDIT = "credit"
    FINANCIAL = "financial"
    OTHER_HIGH_IMPACT = "other_high_impact"
