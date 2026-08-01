from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest


def test_home_page_loads_without_a_running_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_POC_PLANNER_API_BASE_URL", "http://127.0.0.1:9")
    app = AppTest.from_file("streamlit_app.py").run(timeout=10)

    assert not app.exception
    assert [title.value for title in app.title] == ["AI PoC Planner"]
    if app.button:
        assert [button.label for button in app.button] == [
            "建立新專案",
            "查看歷史專案",
            "重新整理",
            "前往模型設定",
        ]
    else:
        assert any("啟動器" in error.value for error in app.error)


@pytest.mark.parametrize(
    ("page_path", "title"),
    [
        ("app_pages/new_project.py", "新建專案"),
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


def test_model_settings_exposes_safe_provider_capability_controls() -> None:
    source = open("app_pages/model_settings.py", encoding="utf-8").read()

    for label in (
        "認證方式",
        "輸出預算欄位",
        "推理參數能力",
        "支援 JSON Schema",
        "支援 JSON Object",
        "清除已保存的 API key",
        "進階相容性設定",
        "private model_profiles.json",
    ):
        assert label in source
    assert "ai_poc_planner.providers" not in source
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.application" not in source


def test_product_guidance_covers_startup_and_blocked_provider_states() -> None:
    home = open("app_pages/home.py", encoding="utf-8").read()
    history = open("app_pages/history.py", encoding="utf-8").read()
    presentation = open(
        "src/ai_poc_planner/ui/presentation.py", encoding="utf-8"
    ).read()

    assert "建立模型設定 → 測試可用性 → 建立專案 → 完成訪談與評估" in home
    assert "查看結果不會重新呼叫模型服務" in history
    assert "模型尚未通過可用性測試" in presentation
    assert "端點、模型名稱、認證方式與結構化輸出能力" in presentation


def test_home_offers_model_settings_action() -> None:
    source = open("app_pages/home.py", encoding="utf-8").read()

    assert 'st.button("前往模型設定"' in source
    assert 'st.switch_page("app_pages/model_settings.py")' in source


def test_global_navigation_contains_only_project_entry_points() -> None:
    source = open("streamlit_app.py", encoding="utf-8").read()

    for label in ("首頁", "新建專案", "專案歷史", "模型設定"):
        assert label in source
    for label in ("需求訪談", "評估結果", "專案工作區"):
        assert label not in source


def test_project_workspace_is_an_internal_supported_streamlit_route() -> None:
    source = open("streamlit_app.py", encoding="utf-8").read()

    assert '"app_pages/discovery.py"' in source
    assert 'visibility="hidden"' in source


def test_workspace_refresh_uses_route_parameters_not_only_session_state() -> None:
    source = open("src/ai_poc_planner/ui/navigation.py", encoding="utf-8").read()

    assert "query_params" in source
    assert "workspace_route_key" in source
    assert "open_workspace" in source
    assert "workspace_target_from_query" in source
