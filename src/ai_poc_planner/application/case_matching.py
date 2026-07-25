"""Deterministic local matching for reviewed cases; no provider is involved."""

from __future__ import annotations

from ai_poc_planner.domain.catalog import OpportunityType
from ai_poc_planner.domain.reviewed_cases import (
    ReviewedCase,
    ReviewedEvidenceGrade,
    ReviewStatus,
)

_GRADE_ORDER = {
    ReviewedEvidenceGrade.A: 0,
    ReviewedEvidenceGrade.B: 1,
    ReviewedEvidenceGrade.C: 2,
    ReviewedEvidenceGrade.D: 3,
}


def match_cases(
    cases: tuple[ReviewedCase, ...],
    opportunity_type: OpportunityType,
    option_kind: str,
    *,
    limit: int = 3,
) -> tuple[ReviewedCase, ...]:
    """Return approved exact-opportunity matches in deterministic evidence order."""

    if limit < 1:
        return ()
    ranked: list[tuple[int, int, str, ReviewedCase]] = []
    query_tags = {opportunity_type.value, option_kind}
    for case in cases:
        if case.review_status is not ReviewStatus.APPROVED:
            continue
        if opportunity_type not in case.opportunity_types:
            continue
        if query_tags.intersection(case.non_applicability_tags):
            continue
        applicability_bonus = int(
            bool(query_tags.intersection(case.applicability_tags))
        )
        ranked.append(
            (
                -applicability_bonus,
                _GRADE_ORDER[case.evidence_grade],
                case.case_id,
                case,
            )
        )
    ranked.sort(key=lambda item: item[:3])
    return tuple(item[3] for item in ranked[:limit])
