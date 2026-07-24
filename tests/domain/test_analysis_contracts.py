from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.analysis import AIAnalysisDraft
from ai_poc_planner.domain.enums import ScoreDimension


def _rating(dimension: ScoreDimension, rating: int = 3) -> dict[str, object]:
    return {
        "dimension": dimension.value,
        "rating": rating,
        "rationale": "Evidence supports a controlled evaluation.",
        "evidence_fact_refs": ["F001"],
        "gap_fact_refs": ["F002"],
        "data_gaps": ["A validation sample is not available."],
        "risks": ["Operational controls require validation."],
        "improvement_conditions": ["Validate the stated condition."],
    }


def _payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "requirement_summary": "Triage requests with human confirmation.",
        "options": [
            {
                "option_key": "rules-first",
                "title": "Rule-based routing first",
                "option_kind": "foundations_first",
                "summary": "Establish labels and rules before an AI PoC.",
                "expected_benefits": ["Faster basic routing"],
                "limitations": ["Exceptions remain manual"],
                "prerequisites": ["Define categories"],
                "risks": ["Rules can become stale"],
                "fact_refs": ["F001"],
                "decision_authority": "human_final_decision",
                "processing_boundary": "local_only",
                "human_review_points": ["A supervisor reviews exceptions"],
                "non_ai_directions": ["rule_based_automation"],
            },
            {
                "option_key": "assistive-ai",
                "title": "Assistive classification candidate",
                "option_kind": "ai",
                "summary": "Offer a local classification suggestion.",
                "expected_benefits": ["Supports staff triage"],
                "limitations": ["Labels need validation"],
                "prerequisites": ["Representative validation data"],
                "risks": ["Incorrect suggestions"],
                "fact_refs": ["F001"],
                "decision_authority": "assistive_only",
                "processing_boundary": "local_only",
                "human_review_points": ["Staff confirms every suggestion"],
                "ai_opportunity": {
                    "kind": "catalog",
                    "opportunity_type": "customer_service_assist",
                    "display_rationale": "Requests need staff assistance.",
                    "fact_refs": ["F001"],
                },
            },
        ],
        "recommended_option_key": "rules-first",
        "conclusion": "establish_non_ai_foundations_before_ai",
        "conclusion_rationale": "The current evidence supports foundations first.",
        "conclusion_fact_refs": ["F001"],
        "rubric_ratings": [_rating(dimension) for dimension in ScoreDimension],
        "gate_signals": [
            {
                "signal_name": "authorization",
                "value": "confirmed",
                "fact_refs": ["F001"],
                "rationale": "The current evidence records authorization.",
            }
        ],
        "overall_risks": ["Data quality remains incomplete."],
        "unresolved_gaps": ["A validation sample is unavailable."],
    }


def test_analysis_contract_accepts_foundations_and_exactly_six_dimensions() -> None:
    model = AIAnalysisDraft.model_validate(_payload())
    assert model.recommended_option_key == "rules-first"
    assert len(model.rubric_ratings) == 6


@pytest.mark.parametrize("field", ["weight", "weighted_points", "weighted_total"])
def test_provider_owned_contract_rejects_program_owned_score_fields(field: str) -> None:
    payload = _payload()
    payload["rubric_ratings"][0][field] = 25  # type: ignore[index]
    with pytest.raises(ValidationError):
        AIAnalysisDraft.model_validate(payload)


def test_recommended_option_must_match_conclusion() -> None:
    payload = _payload()
    payload["conclusion"] = "suitable_for_ai"
    with pytest.raises(ValidationError, match="conflicts with conclusion"):
        AIAnalysisDraft.model_validate(payload)


def test_hybrid_requires_ai_and_non_ai_directions() -> None:
    payload = _payload()
    hybrid = deepcopy(payload["options"][1])  # type: ignore[index]
    hybrid["option_key"] = "hybrid"
    hybrid["option_kind"] = "hybrid"
    payload["options"] = [payload["options"][0], hybrid]  # type: ignore[index]
    payload["recommended_option_key"] = "hybrid"
    payload["conclusion"] = "hybrid_ai_and_non_ai"
    with pytest.raises(ValidationError, match="hybrid options require"):
        AIAnalysisDraft.model_validate(payload)


def test_unknown_gate_signal_name_is_rejected() -> None:
    payload = _payload()
    payload["gate_signals"][0]["signal_name"] = "gate_disposition"  # type: ignore[index]
    with pytest.raises(ValidationError):
        AIAnalysisDraft.model_validate(payload)
