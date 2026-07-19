import subprocess
import sys
from pathlib import Path

import pytest

from ai_poc_planner.__main__ import main


def test_cli_demo_runs_offline_and_writes_report(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "demo.md"
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline demo must not access the network")

    monkeypatch.setattr("socket.create_connection", fail_network)

    exit_code = main(["demo", "--output", str(output)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project: 客服知識檢索 PoC" in captured.out
    assert "Weighted score: 100" in captured.out
    assert "Gate disposition: pass" in captured.out
    assert "Recommendation: 建議進行" in captured.out
    assert output.exists()


def test_cli_without_command_prints_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out


def test_module_demo_process_exits_zero(tmp_path: Path) -> None:
    output = tmp_path / "subprocess-demo.md"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_poc_planner",
            "demo",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Weighted score: 100" in completed.stdout
    assert output.exists()
