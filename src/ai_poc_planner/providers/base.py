"""Small structured provider boundary independent of any model vendor."""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from ai_poc_planner.domain.models import (
    AnalysisProject,
    ContractModel,
    JSONValue,
    PocProposal,
)


class ProviderRequest(ContractModel):
    """Structured context accepted by a proposal-producing provider."""

    project: AnalysisProject
    known_information: dict[str, JSONValue] = Field(default_factory=dict)


class ModelProvider(Protocol):
    """Extension seam for fake, LangChain and OpenAI-compatible adapters."""

    def generate(self, request: ProviderRequest) -> PocProposal:
        """Return a validated structured proposal for the supplied context."""
        ...
