from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_poc_planner.infrastructure.local_case_repository import (
    LocalCaseRepository,
    LocalCaseRepositoryError,
)

_DATA_PATH = Path(__file__).parents[2] / "data" / "reviewed_cases.json"


def test_repository_loads_complete_approved_library_as_immutable_tuple() -> None:
    cases = LocalCaseRepository(_DATA_PATH).load()
    assert len(cases) == 9
    assert isinstance(cases, tuple)
    with pytest.raises(ValidationError):
        cases[0].organization = "Changed"  # type: ignore[misc]


def test_repository_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    records = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    records[1]["case_id"] = records[0]["case_id"]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(LocalCaseRepositoryError, match="duplicate"):
        LocalCaseRepository(path).load()


def test_repository_rejects_any_invalid_record(tmp_path: Path) -> None:
    records = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    records[0]["source_url"] = "not a URL"
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(records), encoding="utf-8")
    with pytest.raises(LocalCaseRepositoryError):
        LocalCaseRepository(path).load()
