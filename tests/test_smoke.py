import subprocess
import sys


def test_module_smoke_command_runs_offline() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "ai_poc_planner"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage: python -m ai_poc_planner" in completed.stdout
