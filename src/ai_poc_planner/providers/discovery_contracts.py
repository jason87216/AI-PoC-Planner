"""Union-free provider DTOs for schema-constrained discovery output."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from ai_poc_planner.domain.discovery import RequirementUnderstanding
from ai_poc_planner.domain.models import ContractModel, NonEmptyStr


class ProviderProposedAssumption(ContractModel):
    fact_key: NonEmptyStr
    value: str
    rationale: NonEmptyStr
    source_fact_ids: list[UUID] = Field(min_length=1)


class ProviderDetectedAmbiguity(ContractModel):
    description: NonEmptyStr
    related_fact_ids: list[UUID] = Field(min_length=1)


class ProviderRequirementUnderstanding(ContractModel):
    """Schema-compatible form of Phase 3 understanding without nullable unions."""

    concise_requirement_summary: NonEmptyStr
    current_workflow_understanding: NonEmptyStr
    desired_outcome_understanding: NonEmptyStr
    available_data_understanding: NonEmptyStr
    users_and_owners_understanding: str
    known_constraints_understanding: str
    proposed_assumptions: list[ProviderProposedAssumption]
    detected_contradictions_or_ambiguities: list[ProviderDetectedAmbiguity]

    def to_domain(self) -> RequirementUnderstanding:
        """Convert the validated provider DTO to the existing durable contract."""

        return RequirementUnderstanding.model_validate(
            {
                **self.model_dump(),
                "users_and_owners_understanding": (
                    self.users_and_owners_understanding.strip() or None
                ),
                "known_constraints_understanding": (
                    self.known_constraints_understanding.strip() or None
                ),
            }
        )
