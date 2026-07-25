"""Assessment and persisted planning-report views."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.results import (
    analysis_overview,
    markdown_download_name,
    report_sections,
    result_view_for_status,
    reviewed_case_sources,
)
from ai_poc_planner.ui.runtime import (
    get_api_client,
    load_analysis,
    load_project_version,
    load_projects,
    load_report,
    refresh_api_data,
)


def _target_from_state() -> tuple[str, int] | None:
    target = st.session_state.get("selected_project")
    if not isinstance(target, dict):
        return None
    project_id, version_number = target.get("project_id"), target.get("version_number")
    if not isinstance(project_id, str) or not isinstance(version_number, int):
        return None
    return project_id, version_number


def _project_name(project_id: str, version_number: int) -> str:
    for project in load_projects():
        if (
            project.get("project_id") == project_id
            and project.get("version_number") == version_number
        ):
            return str(project.get("project_name") or "plan")
    return "plan"


def _recover_latest_target() -> tuple[str, int] | None:
    """Restore the most recently updated result-capable project from the API."""

    for project in load_projects():
        status = result_view_for_status(project.get("status"))
        project_id, version_number = (
            project.get("project_id"),
            project.get("version_number"),
        )
        if (
            status != "unavailable"
            and isinstance(project_id, str)
            and isinstance(version_number, int)
        ):
            target = {"project_id": project_id, "version_number": version_number}
            st.session_state["selected_project"] = target
            return project_id, version_number
    return None


def _items(values: object) -> None:
    if isinstance(values, list) and values:
        for value in values:
            st.write(f"• {value}")
    else:
        st.write("—")


def _render_analysis(analysis: dict[str, Any]) -> None:
    view = analysis_overview(analysis)
    st.subheader("AI 評估結果")
    st.write(view["requirement_summary"])
    first, second, third = st.columns(3)
    first.metric("結論", view["conclusion"], border=True)
    second.metric("加權總分", view["weighted_total"], border=True)
    third.metric("硬性條件", view["gate_disposition"], border=True)
    st.subheader("結論理由")
    st.write(view["conclusion_rationale"])

    st.subheader("建議與替代方向")
    for option in view["options"]:
        heading = str(option["title"])
        if option["recommended"]:
            heading += "（建議方向）"
        with st.expander(heading, expanded=bool(option["recommended"])):
            st.write(option["summary"])
            left, right = st.columns(2)
            with left:
                st.markdown("**預期效益**")
                _items(option["benefits"])
                st.markdown("**前置條件**")
                _items(option["prerequisites"])
                st.markdown("**決策權責**")
                st.write(option["decision_authority"])
            with right:
                st.markdown("**限制**")
                _items(option["limitations"])
                st.markdown("**風險**")
                _items(option["risks"])
                st.markdown("**處理邊界**")
                st.write(option["processing_boundary"])
            st.markdown("**人工覆核重點**")
            _items(option["human_review"])

    st.subheader("六項評分")
    for score in view["scores"]:
        with st.expander(str(score["dimension"])):
            one, two, three = st.columns(3)
            one.metric("評等", score["rating"], border=True)
            two.metric("權重", score["weight"], border=True)
            three.metric("加權分數", score["weighted_points"], border=True)
            st.markdown("**理由**")
            st.write(score["rationale"])
            st.markdown("**資料缺口**")
            _items(score["data_gaps"])
            st.markdown("**風險**")
            _items(score["risks"])
            st.markdown("**改善條件**")
            _items(score["improvement_conditions"])

    st.subheader("硬性條件")
    for number, gate in enumerate(view["gates"], 1):
        with st.expander(f"條件 {number}：{gate['disposition']}"):
            st.write(gate["reason"])
            st.markdown("**必要控制措施**")
            _items(gate["required_controls"])
            st.markdown("**人工覆核**")
            st.write(gate["human_review_required"])
    st.subheader("整體風險")
    _items(view["overall_risks"])
    st.subheader("尚未解決的缺口")
    _items(view["unresolved_gaps"])


def _render_report(
    report: dict[str, Any], project_name: str, version_number: int
) -> None:
    st.subheader("規劃報告")
    for section in report_sections(report):
        with st.expander(section["title"], expanded=section["title"] == "執行摘要"):
            st.write(section["content"])
    cases = reviewed_case_sources(str(report.get("markdown", "")))
    st.subheader("報告中引用的已審閱案例來源")
    if not cases:
        st.info("這份報告未引用已審閱案例來源。")
    for case in cases:
        with st.container(border=True):
            st.write(case["organization"])
            st.caption(f"證據等級：{case['evidence_grade']}")
            st.markdown(f"來源：[{case['source_name']}]({case['source_url']})")
    markdown = str(report.get("markdown", ""))
    st.download_button(
        "下載 Markdown 報告",
        data=markdown.encode("utf-8"),
        file_name=markdown_download_name(project_name, version_number),
        mime="text/markdown",
        icon=":material/download:",
    )


def _refresh_after_write() -> None:
    refresh_api_data()
    st.rerun()


def _render_ready(project_id: str, version_number: int) -> None:
    st.info("訪談已完成，可以開始 AI 評估。")
    if st.button("開始 AI 評估", type="primary", icon=":material/insights:"):
        try:
            with st.spinner("正在建立評估結果，請稍候…"):
                get_api_client().create_analysis(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_assessed(project_id: str, version_number: int, project_name: str) -> None:
    try:
        analysis = load_analysis(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    _render_analysis(analysis)
    if st.button("產生規劃報告", type="primary", icon=":material/article:"):
        try:
            with st.spinner("正在產生規劃報告，請稍候…"):
                get_api_client().create_report(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_complete(project_id: str, version_number: int, project_name: str) -> None:
    try:
        analysis = load_analysis(project_id, version_number)
        report = load_report(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    _render_analysis(analysis)
    _render_report(report, project_name, version_number)


st.title("評估與規劃報告")
if st.button("重新整理結果", icon=":material/refresh:"):
    refresh_api_data()
    st.rerun()

target = _target_from_state()
if target is None:
    try:
        target = _recover_latest_target()
    except ApiClientError as error:
        show_api_error(error)
        target = None
    if target is None:
        st.info("請先從專案歷史選擇一份規劃。")
        if st.button("查看專案歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")
        st.stop()

project_id, version_number = target
try:
    version = load_project_version(project_id, version_number)
    project_name = _project_name(project_id, version_number)
except ApiClientError as error:
    try:
        recovered = _recover_latest_target()
    except ApiClientError:
        recovered = None
    if recovered is None:
        st.session_state["selected_project"] = None
        show_api_error(error)
        st.info("請從專案歷史重新選擇目前版本。")
        st.stop()
    project_id, version_number = recovered
    version = load_project_version(project_id, version_number)
    project_name = _project_name(project_id, version_number)

st.caption(
    f"{project_name} · 第 {version_number} 版 · {status_label(version.get('status'))}"
)
view = result_view_for_status(version.get("status"))
if view == "ready":
    _render_ready(project_id, version_number)
elif view == "assessed":
    _render_assessed(project_id, version_number, project_name)
elif view == "complete":
    _render_complete(project_id, version_number, project_name)
else:
    st.info("這份規劃尚未進入可顯示結果的階段。")
