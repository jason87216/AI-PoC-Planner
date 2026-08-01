from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.planning_report import (
    REPORT_SECTION_KEYS,
    PlanningReportDraft,
    PlanningReportPartA,
    PlanningReportPartB,
    ReportSectionDraft,
)
from ai_poc_planner.providers.json_schema import normalize_provider_schema


def valid_report() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        **{
            key: {"content": f"{key} explanation", "fact_refs": ["F001"]}
            for key in REPORT_SECTION_KEYS
        },
    }


def test_report_requires_every_fixed_section() -> None:
    report = PlanningReportDraft.model_validate(valid_report())
    assert [key for key, _ in report.section_items()] == list(REPORT_SECTION_KEYS)

    invalid = valid_report()
    invalid.pop("executive_summary")
    with pytest.raises(ValidationError):
        PlanningReportDraft.model_validate(invalid)


@pytest.mark.parametrize(
    "field",
    [
        "conclusion",
        "recommended_option_key",
        "recommended_option_kind",
        "weighted_total",
        "gate_disposition",
        "case_id",
        "source_url",
    ],
)
def test_report_forbids_program_owned_fields(field: str) -> None:
    invalid = valid_report()
    invalid[field] = "not-provider-owned"
    with pytest.raises(ValidationError):
        PlanningReportDraft.model_validate(invalid)


def test_report_narration_accepts_digit_free_content_and_fact_tokens() -> None:
    section = ReportSectionDraft(
        content="流程由人工確認並保留稽核軌跡。",
        fact_refs=["F001"],
    )

    assert section.content == "流程由人工確認並保留稽核軌跡。"
    assert section.fact_refs == ["F001"]


@pytest.mark.parametrize(
    "content",
    ["KPI 95%", "第2階段", "2026年", "30天", "cost 100"],
)
def test_report_narration_rejects_ascii_digits(content: str) -> None:
    with pytest.raises(ValidationError):
        ReportSectionDraft(content=content, fact_refs=["F001"])


def test_report_part_schemas_preserve_narration_and_fact_token_patterns() -> None:
    for contract, section_name in (
        (PlanningReportPartA, "executive_summary"),
        (PlanningReportPartB, "deployment_comparison"),
    ):
        schema = normalize_provider_schema(contract.model_json_schema())
        section = schema["properties"][section_name]

        assert section["additionalProperties"] is False
        assert section["properties"]["content"]["pattern"] == r"^[^0-9]+$"
        assert section["properties"]["fact_refs"]["items"]["pattern"] == r"^F[0-9]{3}$"

        serialized = str(schema)
        assert "$ref" not in serialized
        assert "anyOf" not in serialized
        assert "oneOf" not in serialized
        assert "allOf" not in serialized
