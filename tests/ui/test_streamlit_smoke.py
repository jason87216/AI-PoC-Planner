from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest


def test_home_page_loads_without_a_running_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_POC_PLANNER_API_BASE_URL", "http://127.0.0.1:9")
    app = AppTest.from_file("streamlit_app.py").run(timeout=10)

    assert not app.exception
    assert [title.value for title in app.title] == ["AI PoC Planner"]
    assert [button.label for button in app.button] == ["開始新規劃", "重新整理"]


@pytest.mark.parametrize(
    ("page_path", "title"),
    [
        ("app_pages/discovery.py", "新建專案"),
        ("app_pages/history.py", "專案歷史"),
        ("app_pages/results.py", "評估與規劃報告"),
        ("app_pages/model_settings.py", "模型設定"),
    ],
)
def test_product_pages_load_without_a_running_api(
    page_path: str, title: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AI_POC_PLANNER_API_BASE_URL", "http://127.0.0.1:9")
    app = AppTest.from_file(page_path).run(timeout=10)

    assert not app.exception
    assert [item.value for item in app.title] == [title]
