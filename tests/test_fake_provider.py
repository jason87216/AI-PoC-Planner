"""Compatibility-level checks for the public provider exports."""

import pytest
from pydantic import ValidationError

from ai_poc_planner.providers import (
    FakeEmbeddingProvider,
    FakeModelProvider,
    ProviderCapabilities,
    ProviderPreparation,
)


def test_public_provider_types_are_importable() -> None:
    assert FakeModelProvider().capabilities.structured_output is True
    assert FakeEmbeddingProvider().dimensions == 8


def test_ready_preparation_cannot_omit_structured_payload() -> None:
    with pytest.raises(ValidationError, match="requires facts and tool_inputs"):
        ProviderPreparation(status="ready")


def test_provider_capabilities_reject_empty_identifier() -> None:
    with pytest.raises(ValidationError):
        ProviderCapabilities(
            structured_output=True,
            tool_calling=False,
            streaming=False,
            model_identifier="",
        )
