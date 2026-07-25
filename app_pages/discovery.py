"""Product-friendly discovery flow backed exclusively by public FastAPI HTTP."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.discovery import (
    discovery_view_for_status,
    facts_summary,
    interview_payload,
    question_details,
)
from ai_poc_planner.ui.presentation import profile_label, show_api_error
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_current_facts,
    load_discovery_session,
    load_interview_questions,
    load_profiles,
    load_projects,
    load_provider_status,
    load_visible_messages,
    refresh_api_data,
)


def _select_target(project_id: str, version_number: int) -> None:
    st.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": version_number,
    }


def _target() -> tuple[str, int] | None:
    target = st.session_state.get("selected_project")
    if (
        isinstance(target, dict)
        and isinstance(target.get("project_id"), str)
        and isinstance(target.get("version_number"), int)
    ):
        return target["project_id"], target["version_number"]
    try:
        for project in load_projects():
            project_id, number = (
                project.get("project_id"),
                project.get("version_number"),
            )
            if isinstance(project_id, str) and isinstance(number, int):
                load_discovery_session(project_id, number)
                _select_target(project_id, number)
                return project_id, number
    except ApiClientError:
        return None
    return None


def _refresh(*keys: str) -> None:
    for key in keys:
        st.session_state.pop(key, None)
    refresh_api_data()
    st.rerun()


def _understanding(
    session: dict[str, Any], project_id: str, version_number: int
) -> str | None:
    message_id = str(session.get("latest_understanding_message_id") or "")
    for message in load_visible_messages(project_id, version_number):
        if str(message.get("id")) == message_id:
            return str(message.get("content", ""))
    return None


def _provider_ready() -> tuple[bool, str]:
    try:
        status, profiles = load_provider_status(), load_profiles()
    except ApiClientError as error:
        show_api_error(error)
        return False, ""
    if not status.get("formal_analysis_allowed"):
        return False, ""
    selected = next(
        (profile for profile in profiles if profile.get("is_selected")), None
    )
    return selected is not None, profile_label(selected) if selected else ""


def _brief() -> None:
    st.subheader("建立新專案")
    ready, model = _provider_ready()
    if ready:
        st.success(f"目前使用模型：{model}（已通過本次啟動的連線測試）")
    else:
        st.warning("請先在模型設定建立、選擇並測試可用模型，才能整理需求。")
        if st.button("前往模型設定", icon=":material/tune:"):
            st.switch_page("app_pages/model_settings.py")
    with st.form("create_project"):
        project_name = st.text_input(
            "專案名稱", placeholder="例如：內部請購與費用核准流程改善"
        )
        current = st.text_area(
            "目前流程與問題",
            help="說明目前怎麼做、卡在哪裡。",
            placeholder="例如：Excel、紙本與 Email 分散，附件與進度難以追蹤。",
            height=140,
        )
        outcome = st.text_area(
            "希望改善的成果",
            help="描述希望改變的工作成果。",
            placeholder="例如：先統一流程與規則檢查，再評估 AI 是否有幫助。",
            height=120,
        )
        data = st.text_area(
            "現有資料與文件",
            help="可描述文件、歷史紀錄、Excel、資料庫、品質與限制；也可填目前不清楚。",
            placeholder="例如：有紙本、Excel 和 Email，但格式不一致。",
            height=120,
        )
        owners = st.text_area(
            "使用者與負責人", placeholder="例如：申請人、部門主管、財務人員與資訊部門。"
        )
        constraints = st.text_area(
            "已知限制",
            placeholder="例如：正式核准必須由授權主管決定，優先使用 Microsoft 365。",
        )
        submitted = st.form_submit_button(
            "建立專案並整理需求", type="primary", disabled=not ready
        )
    if submitted:
        try:
            created = get_api_client().create_discovery_project(
                {
                    "project_name": project_name,
                    "current_workflow_problem": current,
                    "desired_outcome": outcome,
                    "available_data": data,
                    "users_and_owners": owners or None,
                    "known_constraints": constraints or None,
                }
            )
            project, version = created["project"], created["version"]
            _select_target(str(project["id"]), int(version["version_number"]))
            try:
                get_api_client().generate_understanding(
                    str(project["id"]), int(version["version_number"])
                )
            except ApiClientError:
                st.warning(
                    "專案已建立，但需求理解尚未生成。請使用下方按鈕重新整理需求。"
                )
                refresh_api_data()
            else:
                _refresh()
        except ApiClientError as error:
            show_api_error(error)


def _generation(project_id: str, number: int) -> None:
    st.info("專案已建立，現在可以整理 AI 對需求的理解。")
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
    st.subheader("AI 對需求的理解")
    st.write(summary or "需求理解暫時無法顯示。")
    if st.button("理解正確，繼續", type="primary", icon=":material/check_circle:"):
        try:
            get_api_client().confirm_understanding(project_id, number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh("feedback_text")
    if st.button("需要修改", icon=":material/edit:"):
        st.session_state["show_feedback"] = True
    if st.session_state.get("show_feedback"):
        feedback = st.text_area(
            "請直接說明哪裡不正確，以及正確情況是什麼",
            key="feedback_text",
            placeholder=(
                "例如：第一階段仍必須保留紙本申請，但要把狀態和核准紀錄"
                "統一登記在 Microsoft 365。"
            ),
            height=160,
        )
        if st.button("提交修改並重新整理需求", type="primary"):
            if not feedback.strip():
                st.warning("請先輸入修改內容。")
            else:
                try:
                    get_api_client().submit_understanding_feedback(
                        project_id, number, feedback
                    )
                    get_api_client().generate_understanding(project_id, number)
                except ApiClientError as error:
                    show_api_error(error)
                else:
                    st.session_state.pop("show_feedback", None)
                    _refresh("feedback_text", "show_feedback")


def _next_round(project_id: str, number: int) -> None:
    st.info("AI 只會詢問可能影響方向判斷的少量關鍵問題。")
    if st.button("查看關鍵問題", type="primary", icon=":material/forum:"):
        try:
            get_api_client().generate_interview_round(project_id, number)
        except ApiClientError as error:
            show_api_error(error)
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
    with st.form("key_questions"):
        answers = []
        for index, question in enumerate(questions):
            detail = question_details(question)
            with st.container(border=True):
                st.subheader(detail["question"])
                st.caption(f"為什麼需要確認：{detail['why_it_matters']}")
                answer = st.text_area(
                    "回答",
                    key=f"question_{index}",
                    placeholder="可提供粗略範圍或質性描述。",
                    height=100,
                )
                unknown, missing = st.columns(2)
                unknown_choice = unknown.checkbox("目前不清楚", key=f"unknown_{index}")
                missing_choice = missing.checkbox(
                    "目前沒有相關資料", key=f"missing_{index}"
                )
                status = (
                    "answered"
                    if answer.strip()
                    else (
                        "unknown"
                        if unknown_choice
                        else ("missing" if missing_choice else "")
                    )
                )
                answers.append(
                    {
                        "question_id": str(question["id"]),
                        "answer_status": status,
                        "answer": answer if answer.strip() else None,
                    }
                )
        note = st.text_area(
            "還有其他想補充或更正的內容嗎？（選填）",
            key="supplementary_note",
            placeholder="例如：最終核准必須由部門主管完成；第一階段不能傳送個人資料到未核准的外部服務。",
            height=120,
        )
        submitted = st.form_submit_button("送出回答並繼續", type="primary")
    if submitted:
        if any(not answer["answer_status"] for answer in answers):
            st.warning("請回答每一題，或選擇目前不清楚／目前沒有相關資料。")
            return
        try:
            get_api_client().submit_interview_answers(
                project_id,
                number,
                interview_payload(answers=answers, supplementary_note=note),
            )
        except ApiClientError as error:
            show_api_error(error)
        else:
            keys = ["supplementary_note"] + [
                f"{part}_{i}"
                for i in range(len(questions))
                for part in ("question", "unknown", "missing")
            ]
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
            if project.get("id") == project_id
        ),
        "",
    )
    st.success("需求訪談已完成，可以進入評估階段。")
    st.caption(f"目前專案：{project_name or '已選專案'}｜版本 {number}")
    st.subheader("已確認的需求")
    for item in summary["confirmed"]:
        st.write(f"• {item}")
    st.subheader("目前仍待確認")
    for item in summary["unresolved"]:
        st.write(f"• {item}")
    with st.container(horizontal=True):
        if st.button("查看評估結果", icon=":material/insights:"):
            st.switch_page("app_pages/results.py")
        if st.button("返回首頁", icon=":material/home:"):
            st.switch_page("app_pages/home.py")
        if st.button("查看歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")


st.title("新建專案")
target = _target()
if target is None:
    _brief()
    st.stop()
project_id, version_number = target
try:
    session = load_discovery_session(project_id, version_number)
except ApiClientError as error:
    show_api_error(error)
    st.stop()
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
