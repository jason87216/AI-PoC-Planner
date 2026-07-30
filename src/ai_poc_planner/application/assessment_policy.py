"""Program-owned policy for formal assessment boundaries."""

from __future__ import annotations

from collections.abc import Iterable

from ai_poc_planner.domain.enums import (
    DecisionAuthority,
    FactStatus,
    ProcessingBoundary,
)
from ai_poc_planner.domain.project_history import FactRevision

_LOCAL_ONLY_PATTERNS = (
    "local-only",
    "local only",
    "on-premise",
    "on premises",
    "on-prem",
    "offline only",
    "僅限本機",
    "只能在本機",
    "本機處理",
    "地端處理",
)
_PRIVATE_ENDPOINT_PATTERNS = (
    "private endpoint",
    "private environment",
    "private/internal",
    "private or internal",
    "approved environment",
    "approved internal",
    "external processing is not approved",
    "external model is not approved",
    "do not send to external",
    "not approved for external",
    "僅核准環境",
    "核准環境",
    "脫敏或核准環境",
    "不得送到未核准外部",
    "未核准外部模型",
    "外部模型尚未獲准",
    "外部處理尚未獲准",
)
_EXTERNAL_ENDPOINT_PATTERNS = (
    "approved external processing",
    "external processing is approved",
    "external model is approved",
    "approved external model",
    "may send to external",
    "已核准外部處理",
    "外部處理已獲准",
    "外部模型已獲准",
    "已核准外部模型",
    "允許外部處理",
)
_HUMAN_FINAL_DECISION_PATTERNS = (
    "human final decision",
    "human final approval",
    "manager final approval",
    "主管最終核准",
    "主管保留最終核准",
    "人工最終決策",
    "人工最終核准",
)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(item) for item in value)
    return str(value)


def _confirmed_text(facts: Iterable[FactRevision]) -> str:
    return " ".join(
        _text(fact.value)
        for fact in facts
        if fact.status is FactStatus.CONFIRMED
    ).casefold()


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern.casefold() in text for pattern in patterns)


def derive_processing_boundary(
    facts: Iterable[FactRevision],
) -> ProcessingBoundary:
    """Derive the formal deployment boundary from confirmed project facts.

    Local restrictions take precedence over private restrictions, which in turn
    take precedence over an explicit external-processing approval. Missing or
    conflicting evidence defaults to the conservative local-only boundary.
    """

    confirmed_text = _confirmed_text(facts)
    if _contains_any(confirmed_text, _LOCAL_ONLY_PATTERNS):
        return ProcessingBoundary.LOCAL_ONLY
    if _contains_any(confirmed_text, _PRIVATE_ENDPOINT_PATTERNS):
        return ProcessingBoundary.PRIVATE_ENDPOINT
    if _contains_any(confirmed_text, _EXTERNAL_ENDPOINT_PATTERNS):
        return ProcessingBoundary.EXTERNAL_ENDPOINT
    return ProcessingBoundary.LOCAL_ONLY


def derive_decision_authority(
    facts: Iterable[FactRevision],
) -> DecisionAuthority:
    """Return the current program-owned authority for formal assessment.

    Confirmed human-final-decision facts explicitly support the result. No
    current application policy grants autonomous action, so absent or ambiguous
    evidence remains human-final-decision rather than deferring to a provider.
    """

    confirmed_text = _confirmed_text(facts)
    if _contains_any(confirmed_text, _HUMAN_FINAL_DECISION_PATTERNS):
        return DecisionAuthority.HUMAN_FINAL_DECISION
    return DecisionAuthority.HUMAN_FINAL_DECISION
