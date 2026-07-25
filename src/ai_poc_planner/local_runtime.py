"""Windows-friendly local runtime supervisor for the FastAPI and Streamlit pair."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import uuid
import webbrowser
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx

APPLICATION = "ai-poc-planner"
API_CONTRACT_VERSION = "1"
Mode = Literal["local", "uat"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def data_root(mode: Mode, local_app_data: str | None = None) -> Path:
    root = Path(local_app_data or os.environ.get("LOCALAPPDATA", Path.home()))
    return root / ("AI-PoC-Planner" if mode == "local" else "AI-PoC-Planner-UAT")


@dataclass(frozen=True)
class RuntimeState:
    application: str
    instance_id: str
    launcher_pid: int
    api_pid: int
    streamlit_pid: int
    api_port: int
    streamlit_port: int
    runtime_mode: Mode
    started_at: str


def state_path(root: Path) -> Path:
    return root / "runtime.json"


def write_state(root: Path, state: RuntimeState) -> None:
    root.mkdir(parents=True, exist_ok=True)
    temporary = state_path(root).with_suffix(".tmp")
    temporary.write_text(json.dumps(asdict(state), separators=(",", ":")), "utf-8")
    temporary.replace(state_path(root))


def read_state(root: Path) -> RuntimeState | None:
    try:
        payload = json.loads(state_path(root).read_text("utf-8"))
        return RuntimeState(**payload)
    except (FileNotFoundError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def api_identity(port: int, timeout: float = 1.0) -> dict[str, object] | None:
    try:
        response = httpx.get(
            f"http://127.0.0.1:{port}/v1/runtime-info",
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        )
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    return (
        payload if response.status_code == 200 and isinstance(payload, dict) else None
    )


def state_is_current(state: RuntimeState) -> bool:
    identity = api_identity(state.api_port)
    return bool(
        _pid_exists(state.api_pid)
        and _pid_exists(state.streamlit_pid)
        and identity
        and identity.get("application") == APPLICATION
        and identity.get("instance_id") == state.instance_id
    )


def clear_stale_state(root: Path) -> None:
    state = read_state(root)
    if state is not None and not state_is_current(state):
        state_path(root).unlink(missing_ok=True)


def find_port(start: int, end: int) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port available in {start}-{end}")


def child_environment(api_url: str, instance_id: str) -> dict[str, str]:
    environment = dict(os.environ)
    environment["AI_POC_PLANNER_API_BASE_URL"] = api_url
    environment["AI_POC_PLANNER_INSTANCE_ID"] = instance_id
    return environment


def _wait_for_identity(port: int, instance_id: str, timeout: float = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        identity = api_identity(port)
        if identity and (
            identity.get("application") == APPLICATION
            and identity.get("api_contract_version") == API_CONTRACT_VERSION
            and identity.get("instance_id") == instance_id
        ):
            return True
        time.sleep(0.2)
    return False


def _wait_for_http(url: str, timeout: float = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=1, trust_env=False).status_code < 500:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    return False


def _terminate(process: subprocess.Popen[object], timeout: float = 8) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=timeout)


def start(mode: Mode) -> int:
    root = data_root(mode)
    clear_stale_state(root)
    existing = read_state(root)
    if existing and state_is_current(existing):
        url = f"http://127.0.0.1:{existing.streamlit_port}"
        print(f"既有本機執行個體仍在運行：{url}")
        webbrowser.open(url)
        return 0
    root.mkdir(parents=True, exist_ok=True)
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    instance_id = str(uuid.uuid4())
    api_port, ui_port = find_port(18610, 18699), find_port(18501, 18599)
    python = Path(sys.executable)
    print(f"正在使用 Python：{python}")
    print(f"正在啟動 FastAPI（{api_port}）…")
    api_log = (logs / "api.log").open("a", encoding="utf-8")
    ui_log = (logs / "streamlit.log").open("a", encoding="utf-8")
    api = subprocess.Popen(
        [
            str(python),
            "-m",
            "ai_poc_planner.app.local_server",
            "--database-path",
            str(root / "planner.sqlite3"),
            "--profile-path",
            str(root / "model_profiles.json"),
            "--runtime-mode",
            mode,
            "--instance-id",
            instance_id,
            "--port",
            str(api_port),
        ],
        stdout=api_log,
        stderr=subprocess.STDOUT,
        env=dict(os.environ),
    )
    try:
        if not _wait_for_identity(api_port, instance_id):
            raise RuntimeError("FastAPI 未通过本次启动的身份验证")
        print("FastAPI 已通過身份驗證。正在啟動 Streamlit…")
        api_url = f"http://127.0.0.1:{api_port}"
        ui = subprocess.Popen(
            [
                str(python),
                "-m",
                "streamlit",
                "run",
                "streamlit_app.py",
                "--server.address",
                "127.0.0.1",
                "--server.port",
                str(ui_port),
                "--browser.gatherUsageStats",
                "false",
            ],
            cwd=Path(__file__).resolve().parents[2],
            stdout=ui_log,
            stderr=subprocess.STDOUT,
            env=child_environment(api_url, instance_id),
        )
        url = f"http://127.0.0.1:{ui_port}"
        if not _wait_for_http(url):
            raise RuntimeError("Streamlit 未能在期限內啟動")
        state = RuntimeState(
            APPLICATION,
            instance_id,
            os.getpid(),
            api.pid,
            ui.pid,
            api_port,
            ui_port,
            mode,
            _now(),
        )
        write_state(root, state)
        print(f"產品地址：{url}")
        print(f"日誌位置：{logs}")
        print("按 Ctrl+C 可安全停止兩個本機服務。")
        webbrowser.open(url)
        while True:
            if api.poll() is not None:
                print(f"FastAPI 意外退出（exit code {api.returncode}）。")
                return 3
            if ui.poll() is not None:
                print(f"Streamlit 意外退出（exit code {ui.returncode}）。")
                return 4
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("正在安全停止本機服務…")
        return 0
    finally:
        if "ui" in locals():
            _terminate(ui)
        _terminate(api)
        api_log.close()
        ui_log.close()
        state_path(root).unlink(missing_ok=True)


def stop(mode: Mode) -> int:
    root = data_root(mode)
    state = read_state(root)
    if state is None:
        print("stopped")
        return 0
    if not state_is_current(state):
        state_path(root).unlink(missing_ok=True)
        print("stale")
        return 0
    # Identity plus state match avoids PID-reuse termination. Request a graceful
    # tree stop first, then force only a still-running verified child.
    for pid in (state.streamlit_pid, state.api_pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/T"], check=False)
        deadline = time.monotonic() + 8
        while _pid_exists(pid) and time.monotonic() < deadline:
            time.sleep(0.2)
        if _pid_exists(pid):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"], check=False
            )
    state_path(root).unlink(missing_ok=True)
    print("stopped")
    return 0


def status(mode: Mode) -> int:
    root = data_root(mode)
    state = read_state(root)
    if state is None:
        print("stopped")
    elif state_is_current(state):
        print(
            json.dumps(
                {
                    "status": "running",
                    "runtime_mode": mode,
                    "api_port": state.api_port,
                    "ui_port": state.streamlit_port,
                    "application": APPLICATION,
                    "started_at": state.started_at,
                }
            )
        )
    else:
        print("stale")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="ai-poc-planner.local_runtime")
    parser.add_argument("action", choices=("start", "status", "stop"))
    parser.add_argument("--mode", choices=("local", "uat"), default="local")
    arguments = parser.parse_args()
    return {"start": start, "status": status, "stop": stop}[arguments.action](
        arguments.mode
    )


if __name__ == "__main__":
    raise SystemExit(main())
