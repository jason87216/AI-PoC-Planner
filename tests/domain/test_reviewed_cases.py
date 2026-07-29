from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_poc_planner.domain.reviewed_cases import ReviewedCase

_DATA_PATH = Path(__file__).parents[2] / "data" / "reviewed_cases.json"


def _payload() -> dict[str, object]:
    return json.loads(_DATA_PATH.read_text(encoding="utf-8"))[0]


def test_reviewed_case_library_records_validate() -> None:
    records = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    assert all(
        ReviewedCase.model_validate(record).review_status == "approved"
        for record in records
    )


def test_reviewed_case_library_has_human_maintained_chinese_display_fields() -> None:
    records = json.loads(_DATA_PATH.read_text(encoding="utf-8"))

    assert all(
        record["display_title_zh"] and record["summary_zh"] for record in records
    )


def test_reviewed_case_rejects_missing_source_url() -> None:
    payload = _payload()
    payload.pop("source_url")
    with pytest.raises(ValidationError):
        ReviewedCase.model_validate(payload)


def test_reviewed_case_rejects_grade_e_and_unknown_opportunity() -> None:
    payload = _payload()
    payload["evidence_grade"] = "E"
    with pytest.raises(ValidationError):
        ReviewedCase.model_validate(payload)
    payload = _payload()
    payload["opportunity_types"] = ["unreviewed_opportunity"]
    with pytest.raises(ValidationError):
        ReviewedCase.model_validate(payload)
