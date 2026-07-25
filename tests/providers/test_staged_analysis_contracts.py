"""Regression coverage for the provider-only A0/A1/B analysis boundary."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from ai_poc_planner.application.evidence_analysis import EvidenceAnalysisService
from ai_poc_planner.domain.analysis import OptionKey
from ai_poc_planner.providers.analysis_contracts import (
    option_detail_contract,
    stage_a0_contract,
    stage_b_contract,
)


def _a0() -> dict[str, object]:
    return {
        "recommended_option_index": 1,
        "recommendation_rationale": "Labels need validation before an AI PoC.",
        "recommendation_fact_refs": ["F001"],
        "options": [
            {
                "option_title": "Establish routing foundations",
                "option_kind": "foundations_first",
                "summary": "Standardise labels and routing first.",
                "fact_refs": ["F001"],
            },
            {
                "option_title": "Rule based routing",
                "option_kind": "non_ai",
                "summary": "Use clear channel and category rules.",
                "fact_refs": ["F001"],
            },
        ],
    }


def _detail() -> dict[str, object]:
    return {
        "opportunity_source_kind": "catalog",
        "opportunity_type": "customer_service_assist",
        "candidate_name": "Customer service assist",
        "opportunity_rationale": "Staff need triage assistance.",
        "candidate_definition": "Not used for a catalog opportunity.",
        "why_existing_catalog_is_insufficient": "Not used for a catalog opportunity.",
        "expected_benefits": ["Faster triage"],
        "limitations": ["Needs review"],
        "prerequisites": ["Validated labels"],
        "risks": ["Incorrect suggestion"],
        "human_review_points": ["Staff confirms every suggestion"],
        "fact_refs": ["F001"],
        "decision_authority": "assistive_only",
        "processing_boundary": "private_endpoint",
    }


def test_a0_is_closed_over_confirmed_tokens_and_has_no_detail_fields() -> None:
    contract = stage_a0_contract(("F001",))
    assert contract.model_validate(_a0()).options[0].fact_refs[0].value == "F001"
    payload = _a0()
    payload["options"][0]["not_applicable"] = True  # type: ignore[index]
    with pytest.raises(ValidationError):
        contract.model_validate(payload)
    payload = _a0()
    payload["recommendation_fact_refs"] = ["F999"]
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


def test_a0_rejects_invalid_recommendation_and_same_kind_options() -> None:
    contract = stage_a0_contract(("F001",))
    payload = _a0()
    payload["recommended_option_index"] = 3
    with pytest.raises(ValidationError):
        contract.model_validate(payload)
    payload = _a0()
    payload["options"][1]["option_kind"] = "foundations_first"  # type: ignore[index]
    with pytest.raises(ValidationError, match="alternative"):
        contract.model_validate(payload)


@pytest.mark.parametrize(
    ("option_kind", "expected_conclusion"),
    [
        ("ai", "suitable_for_ai"),
        ("non_ai", "better_suited_to_non_ai"),
        ("foundations_first", "establish_non_ai_foundations_before_ai"),
        ("hybrid", "hybrid_ai_and_non_ai"),
    ],
)
def test_program_derives_conclusion_from_recommended_option_kind(
    option_kind: str, expected_conclusion: str
) -> None:
    assert (
        EvidenceAnalysisService._conclusion_for_kind(option_kind) == expected_conclusion
    )


def test_a0_schema_cannot_accept_model_owned_conclusion() -> None:
    contract = stage_a0_contract(("F001",))
    payload = _a0() | {"conclusion": "suitable_for_ai"}
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


def test_kind_specific_a1_schemas_cannot_accept_other_kind_fields() -> None:
    ai = option_detail_contract("ai", ("F001",))
    assert ai.model_validate(_detail()).opportunity_type == "customer_service_assist"
    non_ai = option_detail_contract("non_ai", ("F001",))
    payload = _detail()
    payload["non_ai_directions"] = ["rule_based_automation"]
    with pytest.raises(ValidationError):
        non_ai.model_validate(payload)
    payload = {
        key: value
        for key, value in payload.items()
        if key
        not in {
            "opportunity_source_kind",
            "opportunity_type",
            "candidate_name",
            "opportunity_rationale",
            "candidate_definition",
            "why_existing_catalog_is_insufficient",
        }
    }
    assert non_ai.model_validate(payload).non_ai_directions == ["rule_based_automation"]


def test_hybrid_and_foundations_require_their_distinct_direction_fields() -> None:
    hybrid = option_detail_contract("hybrid", ("F001",))
    with pytest.raises(ValidationError):
        hybrid.model_validate(_detail())
    foundations = option_detail_contract("foundations_first", ("F001",))
    payload = _detail() | {"non_ai_directions": ["rule_based_automation"]}
    with pytest.raises(ValidationError):
        foundations.model_validate(payload)


def test_stage_b_fixed_fields_close_evidence_and_gap_tokens() -> None:
    contract = stage_b_contract(("F001",), ("F002",))
    rating = {
        "rating": 3,
        "rationale": "Evidence supports a controlled evaluation.",
        "evidence_fact_refs": ["F001"],
        "gap_fact_refs": ["F002"],
        "data_gaps": ["Validation sample is unavailable."],
        "risks": ["Controls need validation."],
        "improvement_conditions": ["Validate a representative sample."],
    }
    payload = {name: rating for name in contract.model_fields}
    assert len(contract.model_validate(payload).model_dump()) == 6
    payload["business_value"] = rating | {"gap_fact_refs": ["F001"]}
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


@pytest.mark.parametrize("option_count", [2, 3, 4])
def test_program_generated_option_keys_are_domain_valid_and_match_selection(
    option_count: int,
) -> None:
    keys = [
        EvidenceAnalysisService._option_key(index)
        for index in range(1, option_count + 1)
    ]
    for key in keys:
        assert TypeAdapter(OptionKey).validate_python(key) == key
    recommended_index = option_count
    recommended = EvidenceAnalysisService._option_key(recommended_index)
    assert recommended == keys[recommended_index - 1]
