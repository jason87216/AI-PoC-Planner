from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.planning_report import (
    REPORT_SECTION_KEYS,
    PlanningReportDraft,
)


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
