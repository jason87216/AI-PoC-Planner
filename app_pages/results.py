"""Readable project results report; all data comes through the FastAPI client."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import ApiClientError
from ai_poc_planner.ui.navigation import (
    switch_page,
    workspace_route_key,
    workspace_target_from_query,
)
from ai_poc_planner.ui.presentation import show_api_error, status_label
from ai_poc_planner.ui.results import (
    analysis_overview,
    markdown_download,
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


def _target_from_query() -> tuple[str, int] | None:
    query_target = workspace_target_from_query()
    if query_target is None:
        return None
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


def _project_name(project_id: str, version_number: int) -> str:
    for project in load_projects():
        if (
            project.get("project_id") == project_id
            and project.get("version_number") == version_number
        ):
            return str(project.get("project_name") or "未命名專案")
    return "未命名專案"


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
        f"{status_label(version.get('status'))} · 使用模型：{model_name or '未記錄'}"
    )
    with st.container(horizontal=True):
        if st.button("返回專案工作區", icon=":material/arrow_back:"):
            switch_page("app_pages/discovery.py")
        if st.button("返回專案歷史", icon=":material/history:"):
            switch_page("app_pages/history.py")


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


def _markdown_table(
    rows: list[dict[str, Any]], fields: tuple[tuple[str, str], ...]
) -> None:
    if not rows:
        st.caption("目前未記錄。")
        return
    headers = [label for _, label in fields]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values: list[str] = []
        for key, _ in fields:
            value = row.get(key, "")
            if isinstance(value, list):
                value = "；".join(str(item) for item in value)
            values.append(str(value).replace("|", "\\|").replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")
    st.markdown("\n".join(lines))


def _render_reviewed_cases(cases: list[dict[str, Any]]) -> None:
    if not cases:
        st.caption("本次沒有匹配的已審核成熟案例。")
        return
    for case in cases:
        st.subheader(str(case.get("display_title_zh", "未命名案例")))
        for label, key in (
            ("背景", "problem_context_zh"),
            ("實際做法", "implemented_approach_zh"),
            ("已記錄成果", "documented_outcomes_zh"),
            ("可借鑑做法", "transferable_practices_zh"),
            ("不直接複製部分", "limitations_zh"),
        ):
            st.markdown(f"- **{label}：** {case.get(key, '')}")
        source_name = case.get("source_name", "來源")
        source_url = case.get("source_url", "")
        st.markdown(f"- **可點擊來源：** [{source_name}]({source_url})")


def _render_synthesis(
    report: dict[str, Any], project_name: str, version_number: int
) -> None:
    view = report_synthesis_view(report)
    if not view:
        st.warning("這份舊版報告沒有新的文章式摘要；以下顯示已保存的 Markdown 內容。")
        markdown = str(report.get("markdown", ""))
        if markdown:
            st.markdown(markdown)
        return

    st.header("1. 專案評估摘要")
    st.write(view["executive_narrative"])
    download = markdown_download(report, project_name, version_number)
    st.download_button(
        "下載 Markdown 報告",
        data=download.data,
        file_name=download.file_name,
        mime=download.mime,
        icon=":material/download:",
    )

    st.header("2. 推薦方案與理由")
    solution = view["recommended_solution"]
    st.subheader(solution["display_name_zh"])
    st.write(solution["short_description_zh"])
    st.markdown(view["recommendation_narrative"])

    st.header("3. 需求與訪談發現")
    _table(
        view["interview_findings"],
        (
            ("topic", "主題"),
            ("confirmed_content", "已確認內容"),
            ("assessment_impact", "對評估的影響"),
        ),
    )

    st.header("4. 方案、成熟案例與專案差距比較")
    st.markdown(view["comparison_narrative"])
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
            ("positioning", "方案定位"),
            ("transferable_practice", "優點"),
            ("cannot_copy", "限制"),
            ("conclusion", "判斷"),
        ),
    )
    if view["reviewed_cases"]:
        st.subheader("成熟案例介紹")
        _render_reviewed_cases(view["reviewed_cases"])
    else:
        st.info("本次沒有匹配的已審核成熟案例。")
    if view["case_support_summaries"]:
        st.subheader("案例支持關係摘要")
        _table(
            view["case_support_summaries"],
            (
                ("case_title", "案例"),
                ("supported_practices", "主要支持做法"),
                ("project_adoption", "本專案採用方式"),
            ),
        )
    st.subheader("官方實施參考")
    reference_rows = [
        {
            **reference,
            "display_title_zh": (
                f"{reference.get('display_title_zh', '')}"
                f"（[{reference.get('source_name', '來源')}]"
                f"({reference.get('source_url', '')})）"
            ),
        }
        for reference in view["implementation_references"]
    ]
    if reference_rows:
        _markdown_table(
            reference_rows,
            (
                ("topic", "主題"),
                ("display_title_zh", "參考文件"),
                ("purpose_zh", "用途"),
            ),
        )
    else:
        st.caption("目前沒有適用的官方實施參考。")
    st.subheader("目前狀態、目標狀態與主要差距")
    _table(
        view["current_target_comparison"],
        (
            ("aspect", "面向"),
            ("current_state", "目前狀態"),
            ("target_state", "採用推薦方案後的目標狀態"),
            ("main_gap", "主要差距"),
            ("treatment", "方案如何處理"),
        ),
    )

    st.header("5. 實施路線、風險與驗收")
    _table(
        view["implementation_roadmap"],
        (
            ("phase", "階段"),
            ("actions", "主要工作"),
            ("outputs", "交付成果"),
            ("human_decision_boundary", "人工邊界"),
            ("acceptance_criteria", "通過條件"),
        ),
    )
    st.markdown("**最重要風險與暫不實施事項**")
    _items(view["major_risks_and_boundaries"])

    with st.expander("6. 技術附錄"):
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
        st.subheader("硬性限制明細")
        _table(
            appendix["hard_gates"],
            (
                ("limit_content", "限制內容"),
                ("affected_stage", "影響階段"),
                ("currently_possible", "目前可做事項"),
                ("release_condition", "重新評估條件"),
            ),
        )


def _refresh_after_write() -> None:
    refresh_api_data()
    st.rerun()


def _render_ready(project_id: str, version_number: int) -> None:
    st.info("需求訪談已完成。接下來會以已確認資訊建立案例與方案評估。")
    if st.button("生成評估報告", type="primary", icon=":material/insights:"):
        try:
            with st.spinner("正在分析需求並評估方案……"):
                get_api_client().create_analysis(project_id, version_number)
            with st.spinner("正在整理完整規劃報告……"):
                get_api_client().create_report(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
            refresh_api_data()
            st.rerun()
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
    st.info("產生規劃報告後，頁面會呈現推薦理由、成熟案例比較、實施路線與硬性限制。")
    if st.button("繼續生成報告", type="primary", icon=":material/article:"):
        try:
            with st.spinner("正在整理正式報告…"):
                get_api_client().create_report(project_id, version_number)
        except ApiClientError as error:
            show_api_error(error)
            refresh_api_data()
            st.rerun()
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
    target = _target_from_query()
if target is None:
    st.title("評估與規劃報告")
    st.info(
        "請先從專案歷史選擇一個已完成訪談的專案；重新進入只會讀取已保存結果，不會重新呼叫模型服務。"
    )
    if st.button("前往專案歷史", icon=":material/history:"):
        switch_page("app_pages/history.py")
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
