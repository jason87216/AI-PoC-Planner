"""Product-friendly discovery flow backed exclusively by public FastAPI HTTP."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.discovery import (
    discovery_view_for_status,
    facts_summary,
    interview_form_key,
    interview_payload,
    interview_widget_key,
    question_details,
    resolve_interview_answer,
    supplementary_note_key,
)
from ai_poc_planner.ui.navigation import (
    open_history,
    open_new_project,
    open_results,
    switch_page,
    workspace_route_key,
    workspace_target_from_query,
)
from ai_poc_planner.ui.presentation import show_api_error
from ai_poc_planner.ui.project_copy import build_project_copy_prefill
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_current_facts,
    load_discovery_session,
    load_interview_questions,
    load_profiles,
    load_projects,
    load_visible_messages,
    refresh_api_data,
)


def _target() -> tuple[str, int] | None:
    target = st.session_state.get("selected_project")
    if (
        isinstance(target, dict)
        and isinstance(target.get("project_id"), str)
        and isinstance(target.get("version_number"), int)
    ):
        return target["project_id"], target["version_number"]
    query_target = workspace_target_from_query()
    if query_target is not None:
        route_key, version_number = query_target
        try:
            project = next(
                project
                for project in load_projects()
                if workspace_route_key(str(project.get("project_id"))) == route_key
                and project.get("version_number") == version_number
            )
        except (ApiClientError, StopIteration):
            return None
        project_id = str(project["project_id"])
        st.session_state["selected_project"] = {
            "project_id": project_id,
            "version_number": version_number,
        }
        return project_id, version_number
    return None


def _refresh(*keys: str) -> None:
    for key in keys:
        st.session_state.pop(key, None)
    refresh_api_data()
    st.rerun()


def _workspace_profile_label(profile: dict[str, Any] | None) -> str:
    if profile is None:
        return "請選擇模型"
    enabled = "可使用" if profile.get("is_enabled") else "已停用"
    return (
        f"{profile.get('profile_name', '未命名設定')}｜"
        f"{profile.get('model_name', '')}｜{enabled}"
    )


def _model_binding(
    project_id: str, version_number: int, version: dict[str, Any]
) -> None:
    snapshot = version.get("selected_model")
    try:
        profiles = load_profiles()
    except ApiClientError as error:
        show_api_error(error)
        return
    bound_id = str(snapshot.get("profile_id")) if isinstance(snapshot, dict) else None
    bound_name = str(snapshot.get("model_name")) if isinstance(snapshot, dict) else None
    bound_profile = next(
        (profile for profile in profiles if str(profile.get("id")) == bound_id), None
    )
    binding_valid = bool(
        bound_profile
        and bound_profile.get("is_enabled")
        and bound_profile.get("model_name") == bound_name
    )
    edit_key = f"workspace_model_edit_{project_id}_{version_number}"
    if binding_valid and not st.session_state.get(edit_key):
        st.caption(
            f"本專案使用的模型服務：{bound_profile.get('profile_name')}｜{bound_profile.get('model_name')}"
        )
        if st.button("更換模型", key=f"change_model_{project_id}_{version_number}"):
            st.session_state[edit_key] = True
            st.rerun()
        return

    st.subheader("更換模型" if snapshot else "選擇模型")
    if isinstance(snapshot, dict) and not bound_profile:
        st.warning("原本綁定的模型設定已不存在；請明確選擇新的模型。")
    elif isinstance(snapshot, dict) and not binding_valid:
        st.warning("原本綁定的模型設定已停用或內容已變更；請重新測試後再保存。")
    if not profiles:
        st.warning("尚未建立可用的模型設定，請先到「模型設定」完成模型可用性測試。")
        if st.button(
            "前往模型設定", key=f"model_settings_{project_id}_{version_number}"
        ):
            switch_page("app_pages/model_settings.py")
        return

    default_index = next(
        (
            index
            for index, profile in enumerate(profiles)
            if str(profile.get("id")) == bound_id
        ),
        None,
    )
    choice = st.selectbox(
        "本專案使用的模型",
        profiles,
        index=default_index,
        format_func=_workspace_profile_label,
        key=f"workspace_profile_{project_id}_{version_number}",
    )
    if choice is None:
        return
    profile_id = str(choice["id"])
    try:
        readiness = get_api_client().profile_status(profile_id)
    except ApiClientError as error:
        show_api_error(error)
        return
    if readiness.get("formal_analysis_allowed"):
        st.success("此模型服務已完成目前執行環境的模型可用性測試。")
    else:
        st.warning("請先完成此模型服務的可用性測試；測試成功後才能保存到本專案。")
        if st.button(
            "測試模型可用性",
            key=f"test_workspace_profile_{project_id}_{version_number}",
        ):
            try:
                tested = get_api_client().test_profile(profile_id)
            except ApiClientError as error:
                show_api_error(error)
            else:
                if tested.get("formal_analysis_allowed"):
                    refresh_api_data()
                    st.rerun()
                else:
                    st.error("模型服務尚未連線成功，請檢查端點、模型名稱與能力設定。")
        return
    if st.button(
        "保存本專案模型",
        type="primary",
        key=f"save_workspace_profile_{project_id}_{version_number}",
    ):
        try:
            get_api_client().bind_project_model_profile(
                project_id, version_number, profile_id
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            st.session_state.pop(edit_key, None)
            refresh_api_data()
            st.rerun()


def _project_heading(
    project_id: str, version_number: int, session: dict[str, Any]
) -> None:
    try:
        project_name = next(
            (
                str(project["project_name"])
                for project in load_projects()
                if project.get("project_id") == project_id
            ),
            "目前專案",
        )
    except ApiClientError as error:
        show_api_error(error)
        project_name = "目前專案"
    phase = {
        "awaiting_understanding_confirmation": "需求確認",
        "brief_submitted": "需求確認",
        "correction_pending": "需求確認",
        "ready_for_interview": "需求訪談",
        "ready_for_next_round": "需求訪談",
        "awaiting_answers": "需求訪談",
        "ready_for_assessment": "訪談完成",
    }.get(str(session.get("status")), "需求確認")
    st.title(project_name)
    try:
        version = get_api_client().get_project_version(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
    else:
        _model_binding(project_id, version_number, version)
    st.caption(f"第 {version_number} 版 · {phase}")
    if st.button("建立其他專案", icon=":material/add:"):
        open_new_project()
    if st.button("複製為新專案", icon=":material/content_copy:"):
        try:
            facts = load_current_facts(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            st.session_state["new_project_prefill"] = build_project_copy_prefill(
                project_name, facts
            )
            open_new_project()


def _understanding(
    session: dict[str, Any], project_id: str, version_number: int
) -> str | None:
    message_id = str(session.get("latest_understanding_message_id") or "")
    for message in load_visible_messages(project_id, version_number):
        if str(message.get("id")) == message_id:
            return str(message.get("content", ""))
    return None


def _brief() -> None:
    """Show navigation only; creation belongs to the independent new-project route."""
    st.info("尚未選取專案。")
    if st.button("前往新建專案", icon=":material/add:"):
        open_new_project()
    if st.button("前往專案歷史", icon=":material/history:"):
        open_history()


def _generation(project_id: str, number: int) -> None:
    st.info("專案已建立。接下來先確認 AI 對需求的理解，再進行訪談。")
    if st.button("整理需求", type="primary", icon=":material/auto_awesome:"):
        try:
            get_api_client().generate_understanding(project_id, number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh("feedback_text")


def _confirmation(session: dict[str, Any], project_id: str, number: int) -> None:
    try:
        summary = _understanding(session, project_id, number)
    except ApiClientError as error:
        show_api_error(error)
        return
    with st.container(border=True):
        st.subheader("AI 對需求的理解")
        st.write(summary or "需求理解暫時無法顯示。")
        st.caption("請確認內容是否符合目前流程、責任與限制；可隨時補充修正。")
        with st.container(horizontal=True):
            confirmed = st.button(
                "確認", type="primary", icon=":material/check_circle:"
            )
            modify = st.button("修改", icon=":material/edit:")
    if confirmed:
        try:
            get_api_client().confirm_understanding(project_id, number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            try:
                with st.spinner("正在整理需要進一步確認的重點……"):
                    get_api_client().generate_interview_round(project_id, number)
            except ApiClientError as error:
                st.session_state["discovery_generation_error"] = error
                refresh_api_data()
                st.rerun()
            else:
                _refresh("feedback_text", "show_feedback")
    if modify:
        st.session_state["show_feedback"] = True
    if st.session_state.get("show_feedback"):
        feedback = st.text_area(
            "請說明需要修改或補充的地方",
            key="feedback_text",
            placeholder=(
                "例如：第一階段不使用 AI 自動判斷權限，而是先由主管從既有"
                "權限範本中選擇，再由系統提醒常見遺漏。"
            ),
            height=160,
        )
        if st.button("提交修改", type="primary"):
            if not feedback.strip():
                st.warning("請先輸入修改內容。")
            else:
                progress = st.status("正在保存修改並重新整理需求理解……", expanded=True)
                try:
                    get_api_client().submit_understanding_feedback(
                        project_id, number, feedback
                    )
                    get_api_client().generate_understanding(project_id, number)
                except ApiClientError as error:
                    progress.update(label="修改需求失敗", state="error")
                    show_api_error(error)
                else:
                    progress.update(label="需求理解已更新", state="complete")
                    st.session_state.pop("show_feedback", None)
                    _refresh("feedback_text", "show_feedback")


def _next_round(project_id: str, number: int) -> None:
    st.warning("需求理解已確認，但問題尚未生成。")
    if st.button("重新產生訪談問題", type="primary", icon=":material/refresh:"):
        try:
            with st.spinner("正在整理需要進一步確認的重點……"):
                get_api_client().generate_interview_round(project_id, number)
        except ApiClientError as error:
            st.session_state["discovery_generation_error"] = error
            refresh_api_data()
            st.rerun()
        else:
            _refresh()


def _answers(session: dict[str, Any], project_id: str, number: int) -> None:
    try:
        questions = [
            q
            for q in load_interview_questions(project_id, number)
            if q.get("round_number") == session.get("current_round")
            and q.get("answer_message_id") is None
        ]
    except ApiClientError as error:
        show_api_error(error)
        return
    round_number = int(session.get("current_round") or 0)

    with st.form(interview_form_key(project_id, number, round_number)):
        answers = []
        for question in questions:
            detail = question_details(question)
            question_id = str(question["id"])
            answer_key = interview_widget_key(
                "answer", project_id, number, round_number, question_id
            )
            status_key = interview_widget_key(
                "status", project_id, number, round_number, question_id
            )
            with st.container(border=True):
                st.subheader(detail["question"])
                st.caption(f"為什麼需要確認：{detail['why_it_matters']}")
                answer_status = st.radio(
                    "回答狀態",
                    options=("提供回答", "目前不清楚", "目前沒有相關資料"),
                    key=status_key,
                )
                answer = st.text_area(
                    "回答",
                    key=answer_key,
                    placeholder="可提供粗略範圍或質性描述。",
                    height=100,
                )
                status, normalized_answer = resolve_interview_answer(
                    answer_status, answer
                )
                answers.append(
                    {
                        "question_id": question_id,
                        "answer_status": status,
                        "answer": normalized_answer,
                    }
                )
        note = st.text_area(
            "還有其他想補充或更正的內容嗎？（選填）",
            key=supplementary_note_key(project_id, number, round_number),
            placeholder="例如：最終核准必須由部門主管完成；第一階段不能傳送個人資料到未核准的外部服務。",
            height=120,
        )
        submitted = st.form_submit_button("送出回答並繼續", type="primary")
    if submitted:
        if any(not answer["answer_status"] for answer in answers):
            st.warning("請回答每一題，或選擇目前不清楚／目前沒有相關資料。")
            return
        try:
            updated = get_api_client().submit_interview_answers(
                project_id,
                number,
                interview_payload(answers=answers, supplementary_note=note),
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            keys = [supplementary_note_key(project_id, number, round_number)] + [
                interview_widget_key(
                    part, project_id, number, round_number, str(question["id"])
                )
                for question in questions
                for part in ("answer", "status")
            ]
            if updated.get("status") == "ready_for_next_round":
                try:
                    with st.spinner("正在整理需要進一步確認的重點……"):
                        get_api_client().generate_interview_round(project_id, number)
                except ApiClientError as error:
                    st.session_state["discovery_generation_error"] = error
                    refresh_api_data()
                    st.rerun()
            _refresh(*keys)


def _complete(project_id: str, number: int) -> None:
    try:
        summary = facts_summary(load_current_facts(project_id, number))
    except ApiClientError as error:
        show_api_error(error)
        return
    project_name = next(
        (
            str(project.get("project_name", ""))
            for project in load_projects()
            if project.get("project_id") == project_id
        ),
        "",
    )
    st.success("需求訪談已完成，可以開始方案評估。")
    st.caption(f"目前專案：{project_name or '已選專案'}｜版本 {number}")
    st.subheader("已確認的需求")
    for item in summary["confirmed"]:
        st.write(f"• {item}")
    st.subheader("目前仍待確認")
    for item in summary["unresolved"]:
        st.write(f"• {item}")
    with st.container(horizontal=True):
        if st.button("生成評估報告", type="primary", icon=":material/insights:"):
            try:
                with st.spinner("正在分析需求並評估方案……"):
                    get_api_client().create_analysis(project_id, number)
            except ApiClientError as error:
                show_api_error(error)
                return
            try:
                with st.spinner("正在整理完整規劃報告……"):
                    get_api_client().create_report(project_id, number)
            except ApiClientError as error:
                refresh_api_data()
                show_api_error(error)
                open_results(project_id, number)
            else:
                refresh_api_data()
                open_results(project_id, number)
        if st.button("返回首頁", icon=":material/home:"):
            switch_page("app_pages/home.py")
        if st.button("查看歷史", icon=":material/history:"):
            switch_page("app_pages/history.py")


def _show_stale_target() -> None:
    st.session_state.pop("selected_project", None)
    st.query_params.clear()
    st.error("找不到這個專案，或專案已經刪除。")
    if st.button("返回專案歷史", icon=":material/history:"):
        open_history()


target = _target()
if target is None:
    if st.query_params.get("workspace"):
        _show_stale_target()
        st.stop()
    st.title("建立新專案")
    _brief()
    st.stop()
project_id, version_number = target
try:
    session = load_discovery_session(project_id, version_number)
except ApiClientError as error:
    if error.code == "project_not_found":
        _show_stale_target()
        st.stop()
    show_api_error(error)
    st.stop()
generation_error = st.session_state.pop("discovery_generation_error", None)
if isinstance(generation_error, ApiClientError):
    show_api_error(generation_error)
_project_heading(project_id, version_number, session)
view = discovery_view_for_status(session.get("status"))
if view == "understanding_generation":
    _generation(project_id, version_number)
elif view == "understanding_confirmation":
    _confirmation(session, project_id, version_number)
elif view == "next_round":
    _next_round(project_id, version_number)
elif view == "interview_answers":
    _answers(session, project_id, version_number)
elif view == "complete":
    _complete(project_id, version_number)
else:
    st.info("此專案目前無法在此頁繼續，請查看專案歷史。")
