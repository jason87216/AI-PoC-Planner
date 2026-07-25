"""Read-only validated loader for the manually reviewed local case library."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from ai_poc_planner.domain.reviewed_cases import ReviewedCase


class LocalCaseRepositoryError(RuntimeError):
    """The complete local library is invalid and cannot be used."""


class LocalCaseRepository:
    """Load all reviewed cases atomically; this repository never writes data."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> tuple[ReviewedCase, ...]:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
            cases = tuple(TypeAdapter(list[ReviewedCase]).validate_python(payload))
        except (OSError, json.JSONDecodeError, ValidationError) as error:
            raise LocalCaseRepositoryError(
                "reviewed case library is invalid"
            ) from error
        case_ids = [case.case_id for case in cases]
        if len(case_ids) != len(set(case_ids)):
            raise LocalCaseRepositoryError(
                "reviewed case library has duplicate case_id"
            )
        return cases
