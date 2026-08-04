from __future__ import annotations

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
        "启动 AI PoC Planner.cmd": "scripts\\start-local.ps1",
        "关闭 AI PoC Planner.cmd": "scripts\\stop-local.ps1",
        "查看运行状态.cmd": "scripts\\status-local.ps1",
    }

    for filename, delegated_script in expectations.items():
        source = read_project_file(filename)
        assert "powershell.exe" in source
        assert delegated_script in source
        assert "-Mode Uat" in source
        assert "local_runtime" not in source


def test_quickstart_artifacts_are_covered_by_existing_ignore_rules() -> None:
    source = read_project_file(".gitignore")

    assert ".venv/" in source
    assert "*.sqlite3" in source
    assert "logs/" in source
