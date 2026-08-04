from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

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
        "安裝 AI PoC Planner.cmd": "setup.ps1",
        "啟動 AI PoC Planner.cmd": "scripts\\start-local.ps1",
    }

    for filename, delegated_script in expectations.items():
        source = read_project_file(filename)
        assert "powershell.exe" in source
        assert delegated_script in source
        assert "%~dp0" in source
        assert "local_runtime" not in source


def test_root_entrypoints_use_traditional_names_and_only_two_are_public() -> None:
    root_entries = {path.name for path in PROJECT_ROOT.glob("*.cmd")}

    assert root_entries == {
        "安裝 AI PoC Planner.cmd",
        "啟動 AI PoC Planner.cmd",
    }
    assert not root_entries & {
        "安装 AI PoC Planner.cmd",
        "启动 AI PoC Planner.cmd",
        "查看运行状态.cmd",
        "关闭 AI PoC Planner.cmd",
        "清除测试资料.cmd",
    }


def test_internal_status_and_stop_scripts_remain_available() -> None:
    assert (PROJECT_ROOT / "scripts/status-local.ps1").is_file()
    assert (PROJECT_ROOT / "scripts/stop-local.ps1").is_file()


def test_install_entrypoint_shows_visible_completion_result() -> None:
    source = read_project_file("安裝 AI PoC Planner.cmd")

    assert "ExecutionPolicy Bypass" in source
    assert "pause" in source.lower()
    assert "powershell.exe" in source


def test_start_entrypoint_pauses_only_when_start_fails() -> None:
    source = read_project_file("啟動 AI PoC Planner.cmd")
    normalized = source.lower()

    assert "pause" in normalized
    assert "if not" in normalized
    assert "exitcode" in normalized
    assert "scripts\\start-local.ps1" in source


def test_setup_uses_traditional_success_guidance_and_no_removed_entries() -> None:
    source = read_project_file("setup.ps1")

    assert "安裝完成。" in source
    assert "請雙擊「啟動 AI PoC Planner.cmd」開始使用。" in source
    assert not any(
        entry in source
        for entry in (
            "查看运行状态.cmd",
            "关闭 AI PoC Planner.cmd",
            "清除测试资料.cmd",
            "reset-uat-data.ps1",
        )
    )


def test_setup_is_utf8_bom_and_parses_with_windows_powershell() -> None:
    setup_path = PROJECT_ROOT / "setup.ps1"
    assert setup_path.read_bytes().startswith(b"\xef\xbb\xbf")

    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is required")

    environment = {"AI_POC_PLANNER_SETUP_PATH": str(setup_path)}
    command = (
        "$source = Get-Content -LiteralPath $env:AI_POC_PLANNER_SETUP_PATH -Raw; "
        "[void][scriptblock]::Create($source); "
        "if ($source.Contains([char]0x5B89) -and "
        "$source.Contains([char]0x88DD) -and "
        "$source.Contains([char]0x555F) -and "
        "$source.Contains([char]0x52D5)) { exit 0 } else { exit 1 }"
    )
    result = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        cwd=PROJECT_ROOT,
        env={**os.environ, **environment},
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")


def test_quickstart_artifacts_are_covered_by_existing_ignore_rules() -> None:
    source = read_project_file(".gitignore")

    assert ".venv/" in source
    assert "*.sqlite3" in source
    assert "logs/" in source


def test_all_cmd_wrappers_are_crlf_and_ascii_only() -> None:
    wrappers = sorted(PROJECT_ROOT.glob("*.cmd"))
    assert {path.name for path in wrappers} == {
        "\u5b89\u88dd AI PoC Planner.cmd",
        "\u555f\u52d5 AI PoC Planner.cmd",
    }

    for path in wrappers:
        data = path.read_bytes()
        assert b"\r\n" in data
        assert b"\n" not in data.replace(b"\r\n", b"")
        data.decode("ascii")


def test_all_cmd_wrappers_have_safe_delegation_contract() -> None:
    expected_scripts = {
        "\u5b89\u88dd AI PoC Planner.cmd": "setup.ps1",
        "\u555f\u52d5 AI PoC Planner.cmd": "scripts\\start-local.ps1",
    }
    runtime_markers = (
        "uvicorn",
        "python -m",
        "local_runtime",
        "venv",
        "localhost",
    )

    for filename, delegated_script in expected_scripts.items():
        source = (PROJECT_ROOT / filename).read_text(encoding="ascii")
        assert "%~dp0" in source
        assert "powershell.exe" in source
        assert delegated_script in source
        assert not any(marker in source.lower() for marker in runtime_markers)


def test_cmd_wrappers_parse_with_cmd_exe_in_temporary_copy(tmp_path: Path) -> None:
    cmd_exe = shutil.which("cmd.exe")
    powershell_exe = shutil.which("powershell.exe")
    if not cmd_exe or not powershell_exe:
        pytest.skip("Windows cmd.exe and powershell.exe are required")

    project_copy = tmp_path / "portfolio copy \u4e2d\u6587"
    scripts_copy = project_copy / "scripts"
    scripts_copy.mkdir(parents=True)

    (project_copy / "setup.ps1").write_text("exit 0\r\n", encoding="ascii")
    (scripts_copy / "start-local.ps1").write_text("exit 0\r\n", encoding="ascii")

    wrappers = sorted(PROJECT_ROOT.glob("*.cmd"))
    for wrapper in wrappers:
        (project_copy / wrapper.name).write_bytes(wrapper.read_bytes())

    expected_codes = {
        "\u5b89\u88dd AI PoC Planner.cmd": 0,
        "\u555f\u52d5 AI PoC Planner.cmd": 0,
    }
    for filename, expected_code in expected_codes.items():
        result = subprocess.run(
            [cmd_exe, "/d", "/c", "call", str(project_copy / filename)],
            cwd=project_copy,
            input=b"\r\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        assert result.returncode == expected_code, result.stdout.decode(
            errors="replace"
        )

    (scripts_copy / "start-local.ps1").write_text("exit 11\r\n", encoding="ascii")
    failed_start = subprocess.run(
        [
            cmd_exe,
            "/d",
            "/c",
            "call",
            str(project_copy / "\u555f\u52d5 AI PoC Planner.cmd"),
        ],
        cwd=project_copy,
        input=b"\r\n",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
        check=False,
    )
    assert failed_start.returncode == 11, failed_start.stdout.decode(errors="replace")
