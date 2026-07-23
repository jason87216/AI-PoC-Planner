"""Provider seams for fake and future model adapters."""

from ai_poc_planner.providers.base import (
    AssessmentToolInputs,
    EmbeddingProvider,
    ModelProvider,
    PreparationStatus,
    ProviderCapabilities,
    ProviderConnectionMessage,
    ProviderConnectionState,
    ProviderError,
    ProviderPreparation,
    ProviderRequest,
)
from ai_poc_planner.providers.fake import (
    FakeEmbeddingProvider,
    FakeModelProvider,
    FakeProviderError,
)
from ai_poc_planner.providers.openai_compatible import (
    OpenAIChatCompletionRequest,
    OpenAIChatMessage,
    OpenAICompatibleChatAdapter,
    OpenAICompatibleProviderError,
)
from ai_poc_planner.providers.profiles import (
    ModelProfile,
    ModelProfilePublic,
    ProviderConnectionStatus,
)

__all__ = [
    "AssessmentToolInputs",
    "EmbeddingProvider",
    "FakeEmbeddingProvider",
    "FakeModelProvider",
    "FakeProviderError",
    "ModelProfile",
    "ModelProfilePublic",
    "ModelProvider",
    "OpenAIChatCompletionRequest",
    "OpenAIChatMessage",
    "OpenAICompatibleChatAdapter",
    "OpenAICompatibleProviderError",
    "ProviderConnectionMessage",
    "ProviderConnectionState",
    "ProviderConnectionStatus",
    "PreparationStatus",
    "ProviderCapabilities",
    "ProviderError",
    "ProviderPreparation",
    "ProviderRequest",
]
