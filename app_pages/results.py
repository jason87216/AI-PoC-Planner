"""Readable project results report; all data comes through the FastAPI client."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.results import (
    analysis_overview,
    markdown_download_name,
    report_synthesis_view,
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
    with st.container(horizontal=True):
        if st.button("返回專案工作區", icon=":material/arrow_back:"):
            st.switch_page("app_pages/discovery.py")
        if st.button("返回專案歷史", icon=":material/history:"):
            st.switch_page("app_pages/history.py")


def _table(rows: list[dict[str, Any]], fields: tuple[tuple[str, str], ...]) -> None:
    if not rows:
        st.caption("目前未記錄。")
        return
    st.table(
        [
            {
                label: (
                    "；".join(value)
                    if isinstance(value := row.get(key), list)
                    else value
                )
                for key, label in fields
            }
            for row in rows
        ]
    )


def _render_synthesis(
    report: dict[str, Any], project_name: str, version_number: int
) -> None:
    view = report_synthesis_view(report)
    if not view:
        st.warning("這份舊版報告沒有文章式 synthesis；以下顯示已保存的 Markdown。")
        markdown = str(report.get("markdown", ""))
        if markdown:
            st.markdown(markdown)
        return

    st.header("1. 專案評估摘要")
    st.write(view["executive_narrative"])
    st.download_button(
        "下載 Markdown 報告",
        data=str(report.get("markdown", "")).encode("utf-8"),
        file_name=markdown_download_name(project_name, version_number),
        mime="text/markdown",
        icon=":material/download:",
    )

    st.header("2. 需求與訪談發現")
    st.write(view["project_context_narrative"])
    _table(
        view["interview_findings"],
        (
            ("topic", "主題"),
            ("initial_understanding", "初始理解"),
            ("clarification", "追問後澄清"),
            ("assessment_impact", "對評估的影響"),
        ),
    )

    st.header("3. 目前狀態與目標狀態")
    _table(
        view["current_target_comparison"],
        (
            ("aspect", "面向"),
            ("current_state", "目前狀態"),
            ("target_state", "目標狀態"),
            ("main_gap", "主要差距"),
            ("treatment", "處理方式"),
        ),
    )

    st.header("4. 候選方案比較")
    option_rows = [
        {
            **row,
            "option": (
                ("正式推薦：" if row.get("recommended") else "")
                + str(row.get("option", ""))
            ),
        }
        for row in view["option_comparison"]
    ]
    _table(
        option_rows,
        (
            ("option", "方案"),
            ("suitable_reason", "適合原因"),
            ("benefits", "效益"),
            ("limitations_risks", "限制／風險"),
            ("prerequisites", "前置條件"),
            ("conclusion", "結論"),
        ),
    )

    st.header("5. 成熟案例橫向比較")
    _table(
        view["case_comparison"],
        (
            ("display_title_zh", "中文案例名稱"),
            ("original_title", "原始英文名稱"),
            ("organization", "組織"),
            ("why_relevant", "為什麼相關"),
            ("transferable_practice", "可移植做法"),
            ("cannot_copy", "不能直接複製"),
            ("adaptation_conclusion", "專案適配結論"),
        ),
    )
    if not view["case_comparison"]:
        st.caption("目前沒有足夠成熟案例作為正式案例依據。")

    st.header("6. 推薦方案與理由")
    st.write(view["recommendation_narrative"])

    st.header("7. 分階段實施路線")
    for phase in view["implementation_roadmap"]:
        st.subheader(phase["phase"])
        st.write(phase["description"])
        for label, key in (
            ("行動", "actions"),
            ("輸入", "inputs"),
            ("輸出", "outputs"),
            ("不做什麼", "not_doing"),
            ("尚存差距", "remaining_gaps"),
            ("驗收條件", "acceptance_criteria"),
        ):
            st.markdown(f"**{label}**")
            _items(phase[key])
        st.markdown(f"**人工決策邊界：** {phase['human_decision_boundary']}")

    st.header("8. 風險、人工邊界與暫不實施事項")
    st.write(view["risk_and_boundary_summary"])
    _table(
        view["hard_gate_summary"],
        (
            ("limit_content", "限制內容"),
            ("affected_stage", "影響階段"),
            ("currently_possible", "目前可做事項"),
            ("release_condition", "解除條件"),
        ),
    )

    st.header("9. 下一步")
    _items(view["next_actions"])

    st.header("10. 評估依據附錄")
    appendix = view["appendix"]
    st.subheader("六維評分")
    _table(
        appendix["scores"],
        (
            ("dimension", "維度"),
            ("judgement", "判斷"),
            ("main_basis", "主要依據"),
            ("improvement_condition", "改善條件"),
        ),
    )
    st.subheader("Hard gate 明細")
    _table(
        appendix["hard_gates"],
        (
            ("gate_id", "編號"),
            ("limit_content", "限制內容"),
            ("affected_stage", "影響階段"),
            ("currently_possible", "目前可做事項"),
            ("release_condition", "解除條件"),
        ),
    )
    st.subheader("安全化原始問答")
    _table(
        appendix["safe_interview_qa"],
        (
            ("question", "問題"),
            ("why_it_matters", "為什麼重要"),
            ("user_answer", "使用者回答"),
            ("assessment_impact", "影響的評估判斷"),
        ),
    )
    st.subheader("證據依據")
    _items(appendix["evidence_basis"])


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


def _render_assessed(project_id: str, version_number: int) -> None:
    try:
        analysis = load_analysis(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    view = analysis_overview(analysis)
    st.header("評估結果已保存")
    st.write(view["conclusion_rationale"])
    st.info("產生正式報告後，頁面會以文章、比較表與附錄呈現完整結果。")
    if st.button("產生正式報告", type="primary", icon=":material/article:"):
        try:
            with st.spinner("正在整理正式報告…"):
                get_api_client().create_report(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
        else:
            _refresh_after_write()


def _render_complete(project_id: str, version_number: int, project_name: str) -> None:
    try:
        report = load_report(project_id, version_number)
    except ApiClientError as error:
        show_api_error(error)
        return
    _render_synthesis(report, project_name, version_number)


st.set_page_config(
    page_title="評估結果", page_icon=":material/article:", layout="centered"
)

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
