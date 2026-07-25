from __future__ import annotations

from pathlib import Path

from ai_poc_planner.application.case_matching import match_cases
from ai_poc_planner.domain.catalog import OpportunityType
from ai_poc_planner.domain.reviewed_cases import ReviewedCase
from ai_poc_planner.infrastructure.local_case_repository import LocalCaseRepository

_DATA_PATH = Path(__file__).parents[2] / "data" / "reviewed_cases.json"


def _cases() -> tuple[ReviewedCase, ...]:
    return LocalCaseRepository(_DATA_PATH).load()


def test_exact_opportunity_matches_return_expected_reviewed_cases() -> None:
    customer = match_cases(_cases(), OpportunityType.CUSTOMER_SERVICE_ASSIST, "ai")
    document = match_cases(
        _cases(), OpportunityType.DOCUMENT_CLASSIFICATION_AND_EXTRACTION, "ai"
    )
    recruiting = match_cases(_cases(), OpportunityType.RECRUITING_PROCESS_ASSIST, "ai")
    assert [(case.case_id, case.organization) for case in customer] == [
        ("case-02", "Klarna")
    ]
    assert [(case.case_id, case.organization) for case in document] == [
        ("case-03", "Affinda")
    ]
    assert [(case.case_id, case.organization) for case in recruiting] == [
        ("case-09", "Gojob")
    ]


def test_non_applicability_tag_excludes_case_and_no_match_returns_empty() -> None:
    excluded = match_cases(
        _cases(), OpportunityType.CUSTOMER_SERVICE_ASSIST, "autonomous_action"
    )
    assert excluded == ()
    no_anomaly_cases = tuple(
        case
        for case in _cases()
        if OpportunityType.ANOMALY_AND_RISK_DETECTION not in case.opportunity_types
    )
    assert (
        match_cases(no_anomaly_cases, OpportunityType.ANOMALY_AND_RISK_DETECTION, "ai")
        == ()
    )


def test_grade_and_case_id_order_are_deterministic() -> None:
    source = _cases()
    a_case = source[1].model_copy(update={"case_id": "case-10", "evidence_grade": "A"})
    b_case = source[1].model_copy(update={"case_id": "case-11", "evidence_grade": "B"})
    c_case = source[1].model_copy(update={"case_id": "case-12", "evidence_grade": "C"})
    first = match_cases(
        (c_case, b_case, a_case), OpportunityType.CUSTOMER_SERVICE_ASSIST, "ai"
    )
    second = match_cases(
        (c_case, b_case, a_case), OpportunityType.CUSTOMER_SERVICE_ASSIST, "ai"
    )
    assert [case.case_id for case in first] == ["case-10", "case-11", "case-12"]
    assert first == second


def test_matcher_is_pure_and_does_not_modify_case_or_analysis_state() -> None:
    cases = _cases()
    before = tuple(case.model_dump(mode="json") for case in cases)
    match_cases(cases, OpportunityType.CUSTOMER_SERVICE_ASSIST, "ai")
    after = tuple(case.model_dump(mode="json") for case in cases)
    assert after == before
