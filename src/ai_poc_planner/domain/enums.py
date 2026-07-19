"""Finite domain states defined by the version 1 specification."""

from enum import StrEnum


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    INTERVIEWING = "interviewing"
    READY_FOR_ASSESSMENT = "ready_for_assessment"
    ASSESSED = "assessed"
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
