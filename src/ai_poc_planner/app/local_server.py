"""Production-only local FastAPI composition and command entry point."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from ai_poc_planner.app.api import create_app
from ai_poc_planner.persistence.model_profiles import LocalModelProfileRepository


class DisabledLegacyChatModel(BaseChatModel):
    """Explicitly disabled legacy planning model; never a fake fallback."""

    @property
    def _llm_type(self) -> str:
        return "disabled-local-runtime"

    def _generate(self, messages: list[BaseMessage], **_: object) -> ChatResult:
        del messages
        raise RuntimeError("legacy planning endpoint is disabled in local runtime")


def create_local_app(
    *,
    database_path: str | Path,
    profile_path: str | Path,
    runtime_mode: str,
    instance_id: str,
):
    """Build the real-provider local app without a fake LangChain model."""

    return create_app(
        chat_model=DisabledLegacyChatModel(),
        database_path=database_path,
        model_profile_repository=LocalModelProfileRepository(path=profile_path),
        runtime_mode=runtime_mode,
        instance_id=instance_id,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-poc-planner-local-server")
    parser.add_argument("--database-path", required=True)
    parser.add_argument("--profile-path", required=True)
    parser.add_argument("--runtime-mode", choices=("local", "uat"), required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args(argv)
    app = create_local_app(
        database_path=arguments.database_path,
        profile_path=arguments.profile_path,
        runtime_mode=arguments.runtime_mode,
        instance_id=arguments.instance_id,
    )
    uvicorn.run(app, host="127.0.0.1", port=arguments.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
