"""Typed, safe fixtures and the shared P6.6 acceptance rubric."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import ConfigDict, Field, TypeAdapter, model_validator

from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.models import ContractModel

_FIXTURE_PATH = Path(__file__).with_name("scenarios.json")
_INITIAL_BRIEF_FIELDS = {
    "project_name",
    "current_workflow_problem",
    "desired_outcome",
    "available_data",
    "users_and_owners",
    "known_constraints",
}
_RUBRIC_DIMENSIONS = (
    ("requirement_understanding", "需求理解準確性"),
    ("human_boundary", "責任與人工決策邊界"),
    ("interview_value", "訪談問題價值"),
    ("case_relevance", "案例相關性"),
    ("case_reference_value", "案例參考價值解釋"),
    ("fit_and_gaps", "專案適配與差距"),
    ("practice_traceability", "可移植做法可追溯性"),
    ("hard_gate_explanation", "hard gates 解釋"),
    ("phased_path", "分階段實施路徑"),
    ("output_consistency", "UI／API／Markdown 一致性"),
)


class FrozenFixture(ContractModel):
    """Strict immutable base for checked-in acceptance data."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AcceptanceFact(FrozenFixture):
    """A deterministic fact used to validate a synthetic scenario."""

    fact_key: str = Field(min_length=1)
    value: Any | None
    status: FactStatus

    @model_validator(mode="after")
    def value_matches_status(self) -> AcceptanceFact:
        requires_value = self.status in {FactStatus.CONFIRMED, FactStatus.ASSUMPTION}
        if requires_value and self.value is None:
            raise ValueError("confirmed and assumption facts require a value")
        if not requires_value and self.value is not None:
            raise ValueError("unknown and missing facts require a null value")
        return self


class AcceptanceBrief(FrozenFixture):
    """Exactly the six fields used by the new-project brief."""

    project_name: str = Field(min_length=1)
    current_workflow_problem: str = Field(min_length=1)
    desired_outcome: str = Field(min_length=1)
    available_data: str = Field(min_length=1)
    users_and_owners: str = Field(min_length=1)
    known_constraints: str = Field(min_length=1)


class AcceptanceInterviewAnswer(FrozenFixture):
    """A standard answer keyed by the purpose of an interview question."""

    question_purpose: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class AcceptanceExpectation(FrozenFixture):
    """Non-exact expected outcomes for deterministic and human review."""

    recommendation_category: Literal[
        "ai_hybrid", "rules_first", "governed_assistive", "readiness_first"
    ]
    opportunity_types: list[str]
    human_decision_boundary: str = Field(min_length=1)
    deployment_constraint: str = Field(min_length=1)
    key_conclusions: list[str] = Field(min_length=1)
    must_have_gap_terms: list[str] = Field(min_length=1)
    must_have_phase_names: list[str] = Field(min_length=1)
    must_not_have_conclusions: list[str] = Field(min_length=1)


class AcceptanceScenario(FrozenFixture):
    """A repeatable synthetic input and its review invariants."""

    scenario_id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1)
    initial_brief: AcceptanceBrief
    understanding_correction: str = Field(min_length=1)
    interview_answers: list[AcceptanceInterviewAnswer] = Field(min_length=1)
    expected: AcceptanceExpectation
    facts: list[AcceptanceFact] = Field(min_length=1)

    @model_validator(mode="after")
    def has_unique_facts_and_six_brief_fields(self) -> AcceptanceScenario:
        fact_keys = [item.fact_key for item in self.facts]
        if len(fact_keys) != len(set(fact_keys)):
            raise ValueError("scenario facts must not repeat fact_key")
        if set(self.initial_brief.model_dump()) != _INITIAL_BRIEF_FIELDS:
            raise ValueError("initial brief must contain exactly six required fields")
        return self


class AcceptanceRubricDimension(FrozenFixture):
    """One human-scored acceptance dimension."""

    key: str = Field(pattern=r"^[a-z_]+$")
    label: str = Field(min_length=1)


class AcceptanceRubric(FrozenFixture):
    """The common 0–2 scorecard used for all four baseline scenarios."""

    dimensions: tuple[AcceptanceRubricDimension, ...] = Field(min_length=10)
    minimum_passing_score: int = Field(ge=0)
    critical_dimension_keys: tuple[str, ...] = Field(min_length=1)

    @property
    def maximum_score(self) -> int:
        return len(self.dimensions) * 2


ACCEPTANCE_RUBRIC = AcceptanceRubric(
    dimensions=tuple(
        AcceptanceRubricDimension(key=key, label=label)
        for key, label in _RUBRIC_DIMENSIONS
    ),
    minimum_passing_score=16,
    critical_dimension_keys=(
        "requirement_understanding",
        "case_relevance",
        "hard_gate_explanation",
    ),
)


def load_acceptance_scenarios(
    path: Path = _FIXTURE_PATH,
) -> tuple[AcceptanceScenario, ...]:
    """Load only the checked-in synthetic fixture; never load provider output."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = tuple(TypeAdapter(list[AcceptanceScenario]).validate_python(payload))
    scenario_ids = [item.scenario_id for item in scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        raise ValueError("scenario_id must be unique")
    return scenarios
