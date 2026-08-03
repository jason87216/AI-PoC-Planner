from __future__ import annotations

import ast
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ai_poc_planner.ui.runtime as runtime


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
        ("app_pages/model_settings_new.py", "新增模型設定"),
        ("app_pages/model_settings_edit.py", "編輯模型設定"),
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
    overview = open("app_pages/model_settings.py", encoding="utf-8").read()
    source = open("app_pages/model_settings_new.py", encoding="utf-8").read()
    source += open("app_pages/model_settings_edit.py", encoding="utf-8").read()

    assert 'st.form("create_model_profile"' not in overview
    assert 'st.form("update_model_profile"' not in overview

    for label in (
        "認證方式",
        "輸出長度參數",
        "推理參數能力",
        "支援嚴格結構化輸出（JSON Schema）",
        "支援一般 JSON 輸出（JSON Object）",
        "清除已保存的 API key",
        "相容性設定（技術人員）",
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


def test_new_project_marks_only_name_and_workflow_as_required() -> None:
    source = open("app_pages/new_project.py", encoding="utf-8").read()

    assert '"專案名稱",' in source
    assert '"目前流程與問題",' in source
    for label in (
        "希望改善的成果（選填）",
        "現有資料與文件（選填）",
        "使用者與負責人（選填）",
        "已知限制（選填）",
    ):
        assert label in source
    assert "後續訪談會協助整理期望成果與驗收方式" in source
    assert "可填寫預算、時程、" in source
    assert "個資、法規、部署環境或人工核准要求" in source


def test_new_project_optional_guidance_is_rendered_as_visible_captions() -> None:
    source = open("app_pages/new_project.py", encoding="utf-8").read()
    tree = ast.parse(source)
    visible_text: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "st":
            continue
        if node.func.attr not in {"caption", "markdown"} or not node.args:
            continue
        try:
            value = ast.literal_eval(node.args[0])
        except (ValueError, TypeError, SyntaxError):
            continue
        if isinstance(value, str):
            visible_text.append(value)

    expected = (
        "尚未確定可先留白，後續訪談會協助整理期望成果與驗收方式。",
        "可列出表單、規範、紀錄或系統資料；不確定可先留白。",
        "可填寫實際使用者、審核者、流程負責人與維運角色；不確定可先留白。",
        "不確定可先留白，後續訪談會協助補充。可填寫預算、時程、"
        "個資、法規、部署環境或人工核准要求。",
    )
    assert all(text in visible_text for text in expected)


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


def test_discovery_interview_form_renders_and_isolates_round_and_project_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id = "project-one"
    other_project_id = "project-two"
    question_id = "question-one"

    class FakeApi:
        current_project = project_id
        current_round = 1
        submitted: list[dict[str, object]] = []

        def get_project_version(self, *_args: object) -> dict[str, object]:
            return {"project_name": "Render test project", "phase": "第一階段 PoC"}

        def profile_status(self, *_args: object) -> dict[str, object]:
            return {"formal_analysis_allowed": True}

        def submit_interview_answers(self, *_args: object) -> dict[str, str]:
            self.submitted.append(_args[-1])
            self.current_round = 2
            return {"status": "ready_for_next_round"}

        def generate_interview_round(self, *_args: object) -> list[dict[str, object]]:
            return []

    fake = FakeApi()

    def load_session(*_args: object) -> dict[str, object]:
        return {
            "status": "awaiting_answers",
            "current_round": fake.current_round,
            "phase": "interview",
        }

    def load_questions(*_args: object) -> list[dict[str, object]]:
        return [
            {
                "id": question_id,
                "round_number": fake.current_round,
                "answer_message_id": None,
                "question": f"Question {fake.current_round}",
                "why_it_matters": "Render safety",
                "affected_judgement": "Data readiness",
                "example": "A short answer",
            }
        ]

    monkeypatch.setattr(runtime, "get_api_client", lambda: fake)
    monkeypatch.setattr(runtime, "load_discovery_session", load_session)
    monkeypatch.setattr(runtime, "load_interview_questions", load_questions)
    monkeypatch.setattr(
        runtime,
        "load_projects",
        lambda: [
            {
                "project_id": fake.current_project,
                "version_number": 1,
                "project_name": "Render test project",
            }
        ],
    )
    monkeypatch.setattr(
        runtime,
        "load_profiles",
        lambda: [
            {
                "id": "profile-1",
                "profile_name": "Test",
                "model_name": "model",
                "is_enabled": True,
            }
        ],
    )
    monkeypatch.setattr(runtime, "load_current_facts", lambda *_args: [])
    monkeypatch.setattr(runtime, "refresh_api_data", lambda: None)

    app = AppTest.from_file(str(Path("app_pages/discovery.py")))
    app.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": 1,
    }
    app.run(timeout=10)

    assert not app.exception
    assert app.radio[0].value == "提供回答"
    assert app.text_area[0].value == ""
    assert app.text_area[1].value == ""

    app.text_area[0].set_value("round one answer")
    next(button for button in app.button if button.label == "送出回答並繼續").click()
    app.run(timeout=10)

    assert not app.exception
    assert fake.submitted[0]["answers"][0]["answer_status"] == "answered"
    assert app.radio[0].value == "提供回答"
    assert app.text_area[0].value == ""
    assert app.text_area[1].value == ""

    fake.current_project = other_project_id
    app.session_state["selected_project"] = {
        "project_id": other_project_id,
        "version_number": 1,
    }
    app.run(timeout=10)

    assert not app.exception
    assert app.radio[0].value == "提供回答"
    assert app.text_area[0].value == ""
    assert app.text_area[1].value == ""
