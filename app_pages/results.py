"""Hidden project results workspace; all data comes through the FastAPI client."""

from __future__ import annotations

import re
from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.results import (
    analysis_overview,
    case_centered_overview,
    markdown_download_name,
    report_sections,
    result_view_for_status,
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
    project_id = target.get("project_id")
    version_number = target.get("version_number")
    if not isinstance(project_id, str) or not isinstance(version_number, int):
        return None
    return project_id, version_number


def _project_name(project_id: str, version_number: int) -> str:
    for project in load_projects():
        if (
            project.get("project_id") == project_id
            and project.get("version_number") == version_number
        ):
            return str(project.get("project_name") or "未命名專案")
    return "未命名專案"


def _recover_latest_target() -> tuple[str, int] | None:
    for project in load_projects():
        project_id = project.get("project_id")
        version_number = project.get("version_number")
        if (
            result_view_for_status(project.get("status")) != "unavailable"
            and isinstance(project_id, str)
            and isinstance(version_number, int)
        ):
            target = {"project_id": project_id, "version_number": version_number}
            st.session_state["selected_project"] = target
            return project_id, version_number
    return None


def _items(values: object, empty: str = "目前未記錄。") -> None:
    if isinstance(values, list) and values:
        for value in values:
            st.markdown(f"- {value}")
    else:
        st.caption(empty)


def _render_header(
    project_name: str, version_number: int, version: dict[str, Any]
) -> None:
    st.title("評估與規劃報告")
    selected_model = version.get("selected_model")
    model_name = (
        selected_model.get("model_name")
        if isinstance(selected_model, dict)
        else version.get("model_name")
    )
    st.caption(
        f"{project_name} · 第 {version_number} 版 · "
        f"{status_label(version.get('status'))} · 模型：{model_name or '未記錄'}"
    )
    left, right = st.columns(2)
    with left:
        if st.button("返回專案工作區", icon=":material/arrow_back:"):
            st.switch_page("app_pages/discovery.py")
    with right:
        if st.button("返回專案歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")


def _render_conclusion(analysis: dict[str, Any]) -> dict[str, Any]:
    view = analysis_overview(analysis)
    case_view = case_centered_overview(analysis)
    st.header("本次評估結論")
    if case_view:
        st.subheader(case_view["recommendation_title"])
        st.write("；".join(case_view["recommendation_basis"]))
        if case_view["matching_status"] != "已匹配":
            st.info(
                case_view["no_case_reason"]
                or "目前沒有足夠成熟案例；以下仍保留 deterministic readiness 與差距。"
            )
    else:
        st.subheader(view["conclusion"])
        st.write(view["conclusion_rationale"])
    return case_view


def _render_cases(case_view: dict[str, Any]) -> None:
    st.header("最相關成熟案例")
    cases = case_view.get("cases", [])
    if not cases:
        st.info(
            case_view.get("no_case_reason")
            or "目前沒有通過審核且與需求相符的成熟案例。"
        )
        return
    for case in cases:
        with st.container(border=True):
            st.subheader(case["title"])
            st.caption(case["organization"])
            first, second = st.columns(2)
            first.metric("案例參考價值", case["reference_level"])
            second.metric("專案適配程度", case["fit_level"])
            st.markdown("**主要相似點**")
            _items(case["similarities"])
            st.markdown("**主要差距**")
            _items(case["differences"])
            with st.expander("查看依據"):
                st.markdown("**參考價值依據**")
                _items(case["reference_basis"])
                st.markdown("**尚未確認**")
                _items(case["reference_unknown"])
                for source in case["sources"]:
                    st.markdown(f"- [{source['label']}]({source['url']})")


def _render_gaps(case_view: dict[str, Any]) -> None:
    st.header("案例比較與關鍵差距")
    for case in case_view.get("cases", []):
        with st.expander(case["title"], expanded=True):
            columns = st.columns(4)
            labels = (
                ("已具備條件", "ready_conditions"),
                ("尚缺條件", "missing_conditions"),
                ("不可直接複製", "not_directly_transferable"),
                ("需要確認", "gap_confirmation"),
            )
            for column, (label, key) in zip(columns, labels, strict=True):
                with column:
                    st.markdown(f"**{label}**")
                    _items(case[key])


def _render_practices(case_view: dict[str, Any]) -> None:
    st.header("可移植做法")
    practices = case_view.get("practices", [])
    if not practices:
        st.info("沒有足夠案例來源可形成正式可移植做法。")
        return
    for practice in practices:
        with st.container(border=True):
            st.subheader(practice["name"])
            st.caption("來源案例：" + "、".join(practice["source_case_titles"]))
            st.write(practice["case_evidence"])
            st.markdown(f"**可移植部分：** {practice['transferable_part']}")
            st.markdown("**必須調整**")
            _items(practice["required_adjustments"])
            st.markdown(f"**目前階段：** {practice['current_stage']}")
            st.markdown("**前置條件**")
            _items(practice["prerequisites"])
            st.markdown("**不適用範圍**")
            _items(practice["not_applicable_scope"])


def _render_constraints(case_view: dict[str, Any]) -> None:
    st.header("當前限制與人工邊界")
    gates = case_view.get("gates", [])
    if not gates:
        st.info("目前沒有額外 hard gate；仍保留人工最終決策。")
    for gate in gates:
        with st.container(border=True):
            st.subheader(gate["affected_stage"])
            st.caption(gate["disposition"])
            st.markdown("**這個 gate 限制**")
            _items(gate["limits"])
            st.markdown("**這個 gate 不限制**")
            _items(gate["does_not_limit"])
            st.markdown("**解除限制需要**")
            _items(gate["release_conditions"])


def _render_path(case_view: dict[str, Any]) -> None:
    st.header("分階段實施路線")
    for phase in case_view.get("phases", []):
        with st.expander(
            phase["phase_name"], expanded=phase["phase_name"] == "第一階段 PoC"
        ):
            st.write(phase["description"])
            for label, key in (
                ("行動", "actions"),
                ("輸入", "inputs"),
                ("輸出", "outputs"),
                ("使用者", "users"),
                ("不做什麼", "not_doing"),
                ("尚存差距", "remaining_gaps"),
                ("驗收指標", "acceptance_criteria"),
            ):
                st.markdown(f"**{label}**")
                _items(phase[key])
            st.markdown(f"**人工決策邊界：** {phase['human_decision_boundary']}")


def _render_scores(analysis: dict[str, Any]) -> None:
    view = analysis_overview(analysis)
    st.header("評分與判定依據")
    st.caption("評分對象：目前專案在現階段採用實施路徑的可行性與準備程度。")
    for score in view["scores"]:
        with st.expander(score["dimension"]):
            st.write(score["rationale"])
            st.caption(
                f"{score['rating']}/5；權重 {score['weight']}；"
                f"加權點數 {score['weighted_points']}"
            )
            st.markdown("**資料未知的影響**")
            _items(score.get("data_gaps"))
            st.markdown("**改善條件**")
            _items(score.get("improvement_conditions"))


def _render_report(
    report: dict[str, Any], project_name: str, version_number: int
) -> None:
    st.header("正式報告")
    markdown = str(report.get("markdown", ""))
    if markdown:
        with st.expander("查看 Markdown 報告", expanded=True):
            st.markdown(re.sub(r"\s*\(?F\d{3}\)?", "", markdown))
    for section in report_sections(report):
        with st.expander(section["title"]):
            st.write(section["content"])
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
    st.info("訪談已完成，可以開始建立這個專案的案例中心評估。")
    if st.button("開始評估", type="primary", icon=":material/insights:"):
        try:
            with st.spinner("正在匹配成熟案例並建立評估結果…"):
                get_api_client().create_analysis(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _load_and_render_assessment(
    project_id: str, version_number: int
) -> dict[str, Any] | None:
    try:
        analysis = load_analysis(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return None
    case_view = _render_conclusion(analysis)
    if case_view:
        _render_cases(case_view)
        _render_gaps(case_view)
        _render_practices(case_view)
        _render_constraints(case_view)
        _render_path(case_view)
    _render_scores(analysis)
    return analysis


def _render_assessed(project_id: str, version_number: int) -> None:
    _load_and_render_assessment(project_id, version_number)
    st.header("正式報告")
    st.info("評估結果已保存；可產生一份與本次評估共用資料的 Markdown 報告。")
    if st.button("產生正式報告", type="primary", icon=":material/article:"):
        try:
            with st.spinner("正在整理正式報告…"):
                get_api_client().create_report(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_complete(project_id: str, version_number: int, project_name: str) -> None:
    _load_and_render_assessment(project_id, version_number)
    try:
        report = load_report(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    _render_report(report, project_name, version_number)


st.set_page_config(page_title="評估結果", page_icon="📊", layout="wide")

target = _target_from_state()
if target is None:
    try:
        target = _recover_latest_target()
    except ApiClientError as error:
        show_api_error(error)
        target = None
    if target is None:
        st.title("評估與規劃報告")
        st.info("請先從專案歷史選擇一個已完成訪談的專案。")
        if st.button("前往專案歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")
        st.stop()

project_id, version_number = target
try:
    version = load_project_version(project_id, version_number)
    project_name = _project_name(project_id, version_number)
except ApiClientError as error:
    show_api_error(error)
    st.stop()

_render_header(project_name, version_number, version)
view = result_view_for_status(version.get("status"))
if view == "ready":
    _render_ready(project_id, version_number)
elif view == "assessed":
    _render_assessed(project_id, version_number)
elif view == "complete":
    _render_complete(project_id, version_number, project_name)
else:
    st.info("這個專案目前沒有可顯示的評估結果。")
