from __future__ import annotations

import json
import socket
from pathlib import Path

from ai_poc_planner.local_runtime import (
    APPLICATION,
    RuntimeState,
    child_environment,
    data_root,
    find_port,
    read_state,
    state_path,
    write_state,
)


def test_local_and_uat_data_roots_are_distinct(tmp_path: Path) -> None:
    assert data_root("local", str(tmp_path)) == tmp_path / "AI-PoC-Planner"
    assert data_root("uat", str(tmp_path)) == tmp_path / "AI-PoC-Planner-UAT"


def test_runtime_state_round_trips_without_secrets(tmp_path: Path) -> None:
    state = RuntimeState(
        APPLICATION, "instance", 1, 2, 3, 18610, 18501, "uat", "2026-01-01T00:00:00Z"
    )
    write_state(tmp_path, state)
    assert read_state(tmp_path) == state
    assert "api_key" not in state_path(tmp_path).read_text("utf-8")
    assert (
        json.loads(state_path(tmp_path).read_text("utf-8"))["application"]
        == APPLICATION
    )


def test_child_environment_hands_off_exact_api_and_instance() -> None:
    environment = child_environment("http://127.0.0.1:18611", "instance")
    assert environment["AI_POC_PLANNER_API_BASE_URL"] == "http://127.0.0.1:18611"
    assert environment["AI_POC_PLANNER_INSTANCE_ID"] == "instance"


def test_preferred_port_is_selected_when_available() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    assert find_port(port, port) == port


def test_occupied_preferred_port_selects_next_port_without_taking_it() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        port = int(occupied.getsockname()[1])
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as available:
            available.bind(("127.0.0.1", port + 1))
        assert find_port(port, port + 1) == port + 1


def test_powershell_launcher_requires_project_venv_and_no_system_fallback() -> None:
    source = Path("scripts/start-local.ps1").read_text(encoding="utf-8")
    assert ".venv\\Scripts\\python.exe" in source
    assert "Test-Path -LiteralPath $python" in source
    assert "local_runtime start --mode" in source


def test_streamlit_command_hides_error_details_in_uat() -> None:
    from ai_poc_planner.local_runtime import streamlit_command

    command = streamlit_command(Path("python"), 18501, "uat")

    assert "--client.showErrorDetails=none" in command
    assert "--client.showErrorLinks=false" in command


def test_streamlit_command_keeps_full_error_details_in_local_dev() -> None:
    from ai_poc_planner.local_runtime import streamlit_command

    command = streamlit_command(Path("python"), 18501, "local")

    assert "--client.showErrorDetails=full" in command
    assert "--client.showErrorLinks=true" in command
