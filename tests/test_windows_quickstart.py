from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_project_file(name: str) -> str:
    return (PROJECT_ROOT / name).read_text(encoding="utf-8")


def test_setup_checks_python_312_and_reuses_existing_venv() -> None:
    source = read_project_file("setup.ps1")

    assert "3.12" in source
    assert ".venv\\Scripts\\python.exe" in source
    assert "-m venv" in source
    assert "Test-Path -LiteralPath $venvPython" in source
    assert "Remove-Item" not in source


def test_setup_installs_only_project_runtime_dependencies_into_venv() -> None:
    source = read_project_file("setup.ps1")

    assert "-m pip install" in source
    assert "-e $ProjectRoot" in source
    assert "--no-input" in source
    assert "CUDA" not in source
    assert "Ollama" not in source
    assert "llama.cpp" not in source


def test_cmd_entrypoints_delegate_to_existing_runtime_scripts() -> None:
    expectations = {
        "安装 AI PoC Planner.cmd": "setup.ps1",
        "启动 AI PoC Planner.cmd": "scripts\\start-local.ps1",
        "关闭 AI PoC Planner.cmd": "scripts\\stop-local.ps1",
        "查看运行状态.cmd": "scripts\\status-local.ps1",
    }

    for filename, delegated_script in expectations.items():
        source = read_project_file(filename)
        assert "powershell.exe" in source
        assert delegated_script in source
        assert "%~dp0" in source
        assert "local_runtime" not in source


def test_reset_entrypoint_delegates_to_uat_script_and_always_pauses() -> None:
    source = read_project_file("清除测试资料.cmd")

    assert "%~dp0" in source
    assert "scripts\\reset-uat-data.ps1" in source
    assert "powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass" in source
    assert "pause" in source.lower()
    assert "exit /b %exitCode%" in source
    assert "planner.sqlite3" not in source


def test_reset_script_is_fixed_to_uat_and_delegates_stop_before_deleting() -> None:
    source = read_project_file("scripts/reset-uat-data.ps1")
    stop_position = source.index("stop-local.ps1")
    delete_position = source.index("Remove-Item")

    assert "AI-PoC-Planner-UAT" in source
    assert "AI-PoC-Planner'" not in source
    assert "-Mode Uat" in source
    assert stop_position < delete_position
    assert "model_profiles.json" not in source
    assert "provider" not in source.lower()
    assert ".venv" not in source
    assert "PATH" not in source
    assert "Remove-Item -Recurse" not in source
    assert "planner.sqlite3" in source
    assert "planner.sqlite3-wal" in source
    assert "planner.sqlite3-shm" in source


def test_reset_confirmation_requires_exact_reset_and_is_safe_for_non_reset() -> None:
    source = read_project_file("scripts/reset-uat-data.ps1")

    assert "-cne 'RESET'" in source
    assert "已取消" in source
    assert "未刪除任何檔案" in source


def test_reset_uat_data_smoke_uses_temporary_localappdata() -> None:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        return

    with tempfile.TemporaryDirectory() as temporary_root:
        uat_root = Path(temporary_root) / "AI-PoC-Planner-UAT"
        uat_root.mkdir()
        for filename in (
            "planner.sqlite3",
            "planner.sqlite3-wal",
            "planner.sqlite3-shm",
        ):
            (uat_root / filename).write_bytes(b"disposable")
        profile = uat_root / "model_profiles.json"
        profile_bytes = b"private-profile-marker"
        profile.write_bytes(profile_bytes)
        logs = uat_root / "logs"
        logs.mkdir()
        (logs / "api.log").write_text("safe log marker", encoding="utf-8")

        environment = os.environ.copy()
        environment["LOCALAPPDATA"] = temporary_root
        command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "reset-uat-data.ps1"),
            "-ConfirmText",
            "RESET",
        ]
        cancel = subprocess.run(
            [*command[:-1], "NO"],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert cancel.returncode == 2
        assert all(
            (uat_root / filename).exists()
            for filename in (
                "planner.sqlite3",
                "planner.sqlite3-wal",
                "planner.sqlite3-shm",
            )
        )

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        assert result.returncode == 0
        assert "UAT 測試資料已清除，模型設定已保留。" in result.stdout
        assert not any(
            (uat_root / filename).exists()
            for filename in (
                "planner.sqlite3",
                "planner.sqlite3-wal",
                "planner.sqlite3-shm",
            )
        )
        assert profile.read_bytes() == profile_bytes
        assert logs.is_dir()

        second = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        assert second.returncode == 0
        assert profile.read_bytes() == profile_bytes


def test_install_entrypoint_shows_success_and_failure_results() -> None:
    source = read_project_file("安装 AI PoC Planner.cmd")

    assert "ExecutionPolicy Bypass" in source
    assert "pause" in source.lower()
    assert "安装完成" in source
    assert "安装未完成" in source


def test_status_and_stop_entrypoints_pause_after_every_run() -> None:
    for filename in ("查看运行状态.cmd", "关闭 AI PoC Planner.cmd"):
        source = read_project_file(filename)
        assert "pause" in source.lower()
        assert "exit /b %exitCode%" in source


def test_start_entrypoint_pauses_only_when_start_fails() -> None:
    source = read_project_file("启动 AI PoC Planner.cmd")
    normalized = source.lower()

    assert "pause" in normalized
    assert "if not" in normalized
    assert "exitcode" in normalized
    assert "scripts\\start-local.ps1" in source


def test_quickstart_artifacts_are_covered_by_existing_ignore_rules() -> None:
    source = read_project_file(".gitignore")

    assert ".venv/" in source
    assert "*.sqlite3" in source
    assert "logs/" in source
