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
    ReasoningEffort,
    StructuredOutputMode,
)
from ai_poc_planner.providers.fake import (
    FakeEmbeddingProvider,
    FakeModelProvider,
    FakeProviderError,
)
from ai_poc_planner.providers.openai_compatible import (
    JSONObjectResponseFormat,
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
    "JSONObjectResponseFormat",
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
    "ReasoningEffort",
    "StructuredOutputMode",
]
