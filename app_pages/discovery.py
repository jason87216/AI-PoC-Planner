"""Phase 3 discovery UI backed exclusively by the public FastAPI boundary."""

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
from ai_poc_planner.ui.presentation import show_api_error
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_current_facts,
    load_discovery_session,
    load_interview_questions,
    load_projects,
    load_visible_messages,
    refresh_api_data,
)


def _select_target(project_id: str, version_number: int) -> None:
    st.session_state["selected_project"] = {
        "project_id": project_id,
        "version_number": version_number,
    }


def _current_target() -> tuple[str, int] | None:
    selected = st.session_state.get("selected_project")
    if isinstance(selected, dict):
        project_id = selected.get("project_id")
        version_number = selected.get("version_number")
        if isinstance(project_id, str) and isinstance(version_number, int):
            return project_id, version_number
    return _restore_latest_discovery_target()


def _restore_latest_discovery_target() -> tuple[str, int] | None:
    """Restore the newest resumable discovery item after a browser refresh."""

    try:
        projects = load_projects()
    except ApiClientError:
        return None
    for project in projects:
        project_id = project.get("project_id")
        version_number = project.get("version_number")
        if not isinstance(project_id, str) or not isinstance(version_number, int):
            continue
        try:
            load_discovery_session(project_id, version_number)
        except ApiClientError:
            continue
        _select_target(project_id, version_number)
        return project_id, version_number
    return None


def _refresh_after_write() -> None:
    refresh_api_data()
    st.rerun()


def _fact_options(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(fact["id"]): fact for fact in facts}


def _fact_label(fact: dict[str, Any]) -> str:
    return str(fact.get("fact_key", "未命名資訊"))


def _value_for_status(status: str, value: str) -> object:
    return value if status == "confirmed" else None


def _display_understanding(
    session: dict[str, Any], project_id: str, version_number: int
) -> None:
    try:
        messages = load_visible_messages(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    message_id = str(session.get("latest_understanding_message_id") or "")
    understanding = next(
        (message for message in messages if str(message.get("id")) == message_id),
        None,
    )
    if understanding is None:
        st.info("需求理解正在準備中，請稍後重新整理。")
        return
    with st.container(border=True):
        st.subheader("AI 的需求理解")
        st.write(str(understanding.get("content", "")))


def _render_brief() -> None:
    st.subheader("建立初始 brief")
    st.caption("請先選擇並測試模型設定；提交後會立即產生需求理解。")
    with st.form("initial_brief"):
        project_name = st.text_input("專案名稱")
        current_workflow_problem = st.text_area("目前問題或工作流程")
        desired_outcome = st.text_area("期望成果")
        available_data = st.selectbox(
            "可用資料",
            options=["不知道", "目前沒有"],
            accept_new_options=True,
            placeholder="選擇或輸入現有資料描述",
        )
        users_and_owners = st.text_input("使用者與負責人（選填）")
        known_constraints = st.text_area("已知限制（選填）")
        submitted = st.form_submit_button("提交 brief", icon=":material/send:")

    if not submitted:
        return
    payload: dict[str, Any] = {
        "project_name": project_name,
        "current_workflow_problem": current_workflow_problem,
        "desired_outcome": desired_outcome,
        "available_data": available_data,
    }
    if users_and_owners:
        payload["users_and_owners"] = users_and_owners
    if known_constraints:
        payload["known_constraints"] = known_constraints
    try:
        created = get_api_client().create_discovery_project(payload)
        project = created["project"]
        version = created["version"]
        project_id = str(project["id"])
        version_number = int(version["version_number"])
        _select_target(project_id, version_number)
        get_api_client().generate_understanding(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
    else:
        _refresh_after_write()


def _render_understanding_generation(project_id: str, version_number: int) -> None:
    st.info("brief 已儲存，尚待產生需求理解。")
    if st.button("產生需求理解", icon=":material/auto_awesome:"):
        try:
            get_api_client().generate_understanding(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_understanding_confirmation(
    session: dict[str, Any], project_id: str, version_number: int
) -> None:
    _display_understanding(session, project_id, version_number)
    try:
        facts = load_current_facts(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return

    with st.container(horizontal=True):
        if st.button("確認理解正確", icon=":material/check_circle:"):
            try:
                get_api_client().confirm_understanding(project_id, version_number)
            except ApiClientError as error:
                show_api_error(error)
            else:
                _refresh_after_write()

    fact_by_id = _fact_options(facts)
    st.subheader("修正需求理解")
    with st.form("understanding_correction"):
        target_fact_id = st.selectbox(
            "要修正的資訊",
            options=list(fact_by_id),
            format_func=lambda item: _fact_label(fact_by_id[item]),
        )
        correction_status = st.selectbox(
            "修正後狀態",
            options=["confirmed", "unknown", "missing"],
            format_func=lambda item: {
                "confirmed": "已確認",
                "unknown": "不知道",
                "missing": "目前沒有",
            }[item],
        )
        correction_value = st.text_area("修正內容")
        correction_reason = st.text_input("修正原因")
        correction_submitted = st.form_submit_button("提交修正並重新產生理解")

    if not correction_submitted:
        return
    if correction_status == "confirmed" and not correction_value.strip():
        st.warning("已確認的修正需要填寫內容。")
        return
    if not correction_reason.strip():
        st.warning("請說明修正原因。")
        return
    payload = {
        "corrections": [
            {
                "target_fact_id": target_fact_id,
                "status": correction_status,
                "value": _value_for_status(correction_status, correction_value),
                "correction_reason": correction_reason,
            }
        ],
        "additional_facts": [],
    }
    try:
        get_api_client().submit_understanding_corrections(
            project_id, version_number, payload
        )
        get_api_client().generate_understanding(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
    else:
        _refresh_after_write()


def _render_next_round(project_id: str, version_number: int) -> None:
    st.info("需求理解已確認，可繼續訪談。")
    if st.button("開始下一輪訪談", icon=":material/forum:"):
        try:
            get_api_client().generate_interview_round(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_answers(
    session: dict[str, Any], project_id: str, version_number: int
) -> None:
    try:
        questions = load_interview_questions(project_id, version_number)
        facts = load_current_facts(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    current_questions = [
        question
        for question in questions
        if question.get("round_number") == session.get("current_round")
        and question.get("answer_message_id") is None
    ]
    if not current_questions:
        st.info("這一輪沒有待回答問題，請重新整理。")
        return

    st.subheader("本輪問題")
    with st.form("interview_answers"):
        answers: list[dict[str, Any]] = []
        for question in current_questions:
            detail = question_details(question)
            with st.container(border=True):
                st.write(detail["question"])
                st.caption(f"為什麼重要：{detail['why_it_matters']}")
                st.caption(f"影響判斷：{detail['affected_judgement']}")
                st.caption(f"例子：{detail['example']}")
                answer_status = st.selectbox(
                    "回答方式",
                    options=["", "answered", "unknown", "missing"],
                    format_func=lambda item: {
                        "": "請選擇",
                        "answered": "輸入答案",
                        "unknown": "不知道",
                        "missing": "目前沒有",
                    }[item],
                    key=f"answer_status_{question['id']}",
                )
                answer_text = st.text_area(
                    "答案",
                    key=f"answer_text_{question['id']}",
                )
                answers.append(
                    {
                        "question_id": str(question["id"]),
                        "answer_status": answer_status,
                        "answer": answer_text if answer_status == "answered" else None,
                    }
                )

        fact_by_id = _fact_options(facts)
        with st.expander("主動補充或修正事實"):
            additional_fact_key = st.text_input("新增事實名稱（選填）")
            additional_status = st.selectbox(
                "新增事實狀態",
                options=["confirmed", "unknown", "missing"],
                format_func=lambda item: {
                    "confirmed": "已確認",
                    "unknown": "不知道",
                    "missing": "目前沒有",
                }[item],
            )
            additional_value = st.text_input("新增事實內容")
            correction_target = st.selectbox(
                "修正既有事實（選填）",
                options=["", *fact_by_id],
                format_func=lambda item: (
                    "不修正" if not item else _fact_label(fact_by_id[item])
                ),
            )
            correction_status = st.selectbox(
                "既有事實的新狀態",
                options=["confirmed", "unknown", "missing"],
                format_func=lambda item: {
                    "confirmed": "已確認",
                    "unknown": "不知道",
                    "missing": "目前沒有",
                }[item],
            )
            correction_value = st.text_input("既有事實的新內容")
            correction_reason = st.text_input("既有事實的修正原因")
        answers_submitted = st.form_submit_button(
            "提交本輪答案", icon=":material/send:"
        )

    if not answers_submitted:
        return
    if any(answer["answer_status"] == "" for answer in answers):
        st.warning("請完成本輪每一題，或選擇不知道／目前沒有。")
        return
    if any(
        answer["answer_status"] == "answered" and not str(answer["answer"]).strip()
        for answer in answers
    ):
        st.warning("選擇輸入答案的問題不能留白。")
        return
    if (
        additional_fact_key
        and additional_status == "confirmed"
        and not additional_value
    ):
        st.warning("已確認的新增事實需要填寫內容。")
        return
    if correction_target and correction_status == "confirmed" and not correction_value:
        st.warning("已確認的修正需要填寫內容。")
        return
    if correction_target and not correction_reason:
        st.warning("請說明既有事實的修正原因。")
        return
    additional_fact = (
        {
            "fact_key": additional_fact_key,
            "status": additional_status,
            "value": _value_for_status(additional_status, additional_value),
        }
        if additional_fact_key
        else None
    )
    correction = (
        {
            "target_fact_id": correction_target,
            "status": correction_status,
            "value": _value_for_status(correction_status, correction_value),
            "correction_reason": correction_reason,
        }
        if correction_target
        else None
    )
    try:
        get_api_client().submit_interview_answers(
            project_id,
            version_number,
            interview_payload(
                answers=answers,
                additional_fact=additional_fact,
                correction=correction,
            ),
        )
    except ApiClientError as error:
        show_api_error(error)
    else:
        _refresh_after_write()


def _render_complete(project_id: str, version_number: int) -> None:
    try:
        summary = facts_summary(load_current_facts(project_id, version_number))
    except ApiClientError as error:
        show_api_error(error)
        return
    st.success("訪談已完成，規劃已可進入下一個階段。")
    st.subheader("已確認資訊")
    if summary["confirmed"]:
        st.table(summary["confirmed"])
    else:
        st.info("目前沒有已確認資訊。")
    st.subheader("仍未知或缺失的資訊")
    if summary["unknown_or_missing"]:
        st.table(summary["unknown_or_missing"])
    else:
        st.info("沒有仍未知或缺失的資訊。")
    with st.container(horizontal=True):
        if st.button("返回首頁", icon=":material/home:"):
            st.switch_page("app_pages/home.py")
        if st.button("查看歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")


st.title("新建規劃")
target = _current_target()
if target is None:
    _render_brief()
    st.stop()

project_id, version_number = target
if st.button("開始另一份規劃", icon=":material/add:"):
    st.session_state["selected_project"] = None
    st.rerun()

session_slot = st.container()
with session_slot.skeleton():
    try:
        session = load_discovery_session(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        st.stop()

view = discovery_view_for_status(session.get("status"))
if view == "understanding_generation":
    _render_understanding_generation(project_id, version_number)
elif view == "understanding_confirmation":
    _render_understanding_confirmation(session, project_id, version_number)
elif view == "next_round":
    _render_next_round(project_id, version_number)
elif view == "interview_answers":
    _render_answers(session, project_id, version_number)
elif view == "complete":
    _render_complete(project_id, version_number)
else:
    st.info("這份規劃目前無法在此頁繼續，請返回專案歷史。")
