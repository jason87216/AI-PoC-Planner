"""Single-page Streamlit presentation for persisted AI PoC planning runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from ai_poc_planner.ui.api_client import StreamlitApiClient, UiApiError

_LIST_FIELDS = {"target_users", "data_sources"}
_BOOLEAN_FIELDS = {
    "external_processing_allowed",
    "offline_operation_required",
    "approved_isolated_environment",
}
_DATA_CLASSIFICATIONS = [
    "public",
    "internal",
    "confidential",
    "highly_confidential",
]


def answers_from_form_values(
    questions: Sequence[Mapping[str, Any]],
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep API-supplied field names while converting the small known demo inputs."""

    answers: dict[str, Any] = {}
    for question in questions:
        field = question.get("field")
        if not isinstance(field, str) or field not in values:
            continue
        value = values[field]
        if field in _LIST_FIELDS and isinstance(value, str):
            answers[field] = [
                item.strip() for item in value.splitlines() if item.strip()
            ]
        elif isinstance(value, str):
            answers[field] = value.strip()
        else:
            answers[field] = value
    return answers


def markdown_download_payload(markdown_report: str) -> bytes:
    """Return the exact UTF-8 bytes offered by the Markdown download button."""

    return markdown_report.encode("utf-8")


def main() -> None:
    st.set_page_config(page_title="AI PoC Planner 展示", page_icon="🧭", layout="wide")
    _initialize_state()
    _render_sidebar()
    client = StreamlitApiClient(st.session_state.api_base_url)
    st.title("AI PoC Planner")
    st.caption("單一 persisted planning run 的本機展示介面")
    st.warning(
        "Scripted demo：這個 fake mode 只展示固定流程與 typed tool 整合；"
        "它不會理解或分析你輸入的自然語言需求。"
    )

    _render_create_form(client)
    response = st.session_state.last_api_response
    if not isinstance(response, dict):
        st.info("輸入需求後建立規劃，或在側邊欄輸入 run ID 載入既有結果。")
        return

    _render_stage(response)
    _render_interaction_summary(response)
    _render_clarification_form(client, response)
    _render_planning_information(response)
    if response.get("status") == "completed":
        _render_completed_result(response)

    with st.expander("結構化 API 結果（技術展示）", expanded=False):
        st.json(response)


def _initialize_state() -> None:
    defaults: dict[str, Any] = {
        "api_base_url": "http://127.0.0.1:8000",
        "current_run_id": "",
        "run_id_input": "",
        "planning_request_draft": "",
        "clarification_draft_values": {},
        "last_api_response": None,
        "interaction_timeline": [],
        "health_status": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("連線與既有 run")
        st.text_input("API base URL", key="api_base_url")
        client = StreamlitApiClient(st.session_state.api_base_url)
        if st.button("健康檢查", use_container_width=True):
            try:
                st.session_state.health_status = client.health()
            except UiApiError as error:
                _show_api_error(error)
        health_status = st.session_state.health_status
        if isinstance(health_status, dict):
            st.success(f"API 狀態：{health_status.get('status', 'unknown')}")

        with st.form("load-existing-run"):
            st.text_input("Run ID", key="run_id_input")
            load_requested = st.form_submit_button("載入既有 run")
        if load_requested:
            run_id = st.session_state.run_id_input.strip()
            if not run_id:
                st.warning("請先輸入 run ID。")
            else:
                try:
                    _store_response(client.get_run(run_id), loaded=True)
                except UiApiError as error:
                    _show_api_error(error)


def _render_create_form(client: StreamlitApiClient) -> None:
    st.subheader("建立規劃")
    with st.form("create-planning-run"):
        request = st.text_area(
            "自然語言需求",
            key="planning_request_draft",
            placeholder="例如：客服團隊想更快找到已核准的 FAQ 回覆內容。",
        )
        create_requested = st.form_submit_button("建立 persisted planning run")
    if not create_requested:
        return
    if not request.strip():
        st.warning("請輸入自然語言需求。")
        return
    try:
        _store_response(client.create_run(request.strip()), loaded=False)
    except UiApiError as error:
        _show_api_error(error)


def _render_stage(response: Mapping[str, Any]) -> None:
    status = response.get("status")
    labels = {
        "clarification_required": ("等待補充資訊", "running"),
        "completed": ("規劃完成", "complete"),
        "failed": ("規劃未完成", "error"),
    }
    label, state = labels.get(status, ("正在建立規劃", "running"))
    with st.status(label, state=state, expanded=False):
        st.write(f"目前 run ID：{response.get('run_id', 'unknown')}")


def _render_interaction_summary(response: Mapping[str, Any]) -> None:
    st.subheader("需求與補充資訊")
    timeline = st.session_state.interaction_timeline
    if timeline:
        for item in timeline:
            st.markdown(f"**{item['title']}**")
            st.write(item["content"])
        return

    st.markdown("**原始需求**")
    st.write(response.get("original_request", "—"))
    known_information = response.get("known_information", {})
    if isinstance(known_information, dict) and known_information:
        st.markdown("**累積業務資訊摘要**")
        for field, value in known_information.items():
            st.write(f"• {field}：{_summary_value(value)}")
    else:
        st.caption("此 run 尚未保存補充資訊。")


def _render_clarification_form(
    client: StreamlitApiClient,
    response: Mapping[str, Any],
) -> None:
    if response.get("status") != "clarification_required":
        return
    questions = response.get("clarifying_questions", [])
    if not isinstance(questions, list) or not questions:
        st.warning("API 未回傳可提交的澄清問題。")
        return

    st.subheader("目前澄清問題")
    values: dict[str, Any] = {}
    with st.form(f"clarifications-{response.get('run_id', 'current')}"):
        for question in questions:
            if not isinstance(question, dict) or not isinstance(
                question.get("field"), str
            ):
                continue
            field = question["field"]
            st.markdown(f"**{question.get('question', field)}**")
            st.caption(str(question.get("reason", "")))
            values[field] = _clarification_widget(field)
        submitted = st.form_submit_button("提交這一批答案")

    if not submitted:
        return
    answers = answers_from_form_values(questions, values)
    if not answers or any(_is_blank(value) for value in answers.values()):
        st.warning("請完成目前批次的所有問題後再提交。")
        return
    try:
        _append_clarification_timeline(questions, answers)
        _store_response(
            client.submit_clarifications(str(response["run_id"]), answers),
            loaded=False,
        )
        st.session_state.clarification_draft_values = {}
    except UiApiError as error:
        _show_api_error(error)


def _clarification_widget(field: str) -> Any:
    key = f"clarification-{st.session_state.current_run_id}-{field}"
    if field == "data_classification":
        return st.selectbox("資料分級", _DATA_CLASSIFICATIONS, key=key)
    if field in _BOOLEAN_FIELDS:
        return st.radio(
            "請選擇",
            options=[True, False],
            format_func=lambda value: "是" if value else "否",
            key=key,
            horizontal=True,
        )
    if field in _LIST_FIELDS:
        return st.text_area("每行一項", key=key)
    return st.text_input("你的回答", key=key)


def _render_planning_information(response: Mapping[str, Any]) -> None:
    st.subheader("規劃中間資訊")
    opportunity_match = response.get("opportunity_match", {})
    if isinstance(opportunity_match, dict):
        candidates = opportunity_match.get("candidates", [])
        if isinstance(candidates, list) and candidates:
            st.markdown("### AI opportunity candidates")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                st.markdown(f"**{_display_label(candidate.get('opportunity_type'))}**")
                st.write(f"匹配強度：{candidate.get('match_strength', '—')}")
                _render_text_items("匹配理由", candidate.get("reasons"))
                _render_text_items("仍缺資訊", candidate.get("missing_information"))
        alternatives = opportunity_match.get("non_ai_alternatives", [])
        if isinstance(alternatives, list) and alternatives:
            st.markdown("### Non-AI alternatives")
            st.write("、".join(_display_label(item) for item in alternatives))

    deployment = response.get("deployment_posture", {})
    if isinstance(deployment, dict):
        st.markdown("### Deployment posture")
        recommended = deployment.get("recommended_posture")
        if recommended:
            st.write(f"建議姿態：{_display_label(recommended)}")
        _render_text_items(
            "尚缺部署資訊", deployment.get("missing_deployment_information")
        )
        candidates = deployment.get("candidates", [])
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                st.markdown(
                    f"**{_display_label(candidate.get('posture'))}** "
                    f"（{_display_label(candidate.get('status'))}）"
                )
                _render_text_items("理由", candidate.get("reasons"))
                _render_text_items("必要條件", candidate.get("critical_assumptions"))


def _render_completed_result(response: Mapping[str, Any]) -> None:
    assessment = response.get("assessment")
    proposal = response.get("proposal")
    markdown_report = response.get("markdown_report")
    if not isinstance(assessment, dict) or not isinstance(proposal, dict):
        st.error("completed run 缺少正式 assessment 或 proposal。")
        return

    st.subheader("正式評估與建議")
    score_column, gate_column, recommendation_column = st.columns(3)
    score_column.metric("Weighted score", assessment.get("weighted_score", "—"))
    gate_column.metric(
        "Hard-gate disposition", _display_label(assessment.get("gate_disposition"))
    )
    recommendation_column.metric(
        "Recommendation", _display_label(assessment.get("recommendation"))
    )

    st.markdown("### Six dimensions")
    for score in assessment.get("scores", []):
        if not isinstance(score, dict):
            continue
        st.markdown(
            f"**{_display_label(score.get('dimension'))}**："
            f"{score.get('rating', '—')} / 5（權重 {score.get('weight', '—')}%）"
        )
        st.write(score.get("rationale", ""))

    st.markdown("### Hard gates")
    for gate in assessment.get("hard_gates", []):
        if not isinstance(gate, dict):
            continue
        st.markdown(
            f"**{gate.get('rule_id', 'gate')}："
            f"{_display_label(gate.get('disposition'))}**"
        )
        st.write(gate.get("reason", ""))
        _render_text_items("Required controls", gate.get("required_controls"))

    st.markdown("### PoC proposal")
    st.write(proposal.get("executive_summary") or proposal.get("problem_statement", ""))
    _render_text_items("KPI", proposal.get("success_metrics"))
    _render_text_items("In scope", proposal.get("in_scope"))
    _render_text_items("Out of scope", proposal.get("out_of_scope"))
    _render_text_items("Risks", proposal.get("risks"))
    _render_text_items("Human review / controls", proposal.get("human_review_points"))
    _render_text_items("Next actions", proposal.get("next_actions"))

    if isinstance(markdown_report, str):
        st.subheader("Markdown report")
        st.markdown(markdown_report)
        with st.expander("Markdown 原文（可使用元件內建複製）", expanded=False):
            st.code(markdown_report, language="markdown")
        st.download_button(
            "下載 Markdown report",
            data=markdown_download_payload(markdown_report),
            file_name=f"ai-poc-plan-{response.get('run_id', 'report')}.md",
            mime="text/markdown",
        )


def _store_response(response: dict[str, Any], *, loaded: bool) -> None:
    st.session_state.last_api_response = response
    st.session_state.current_run_id = str(response.get("run_id", ""))
    if loaded:
        st.session_state.interaction_timeline = []
    else:
        original_request = response.get("original_request")
        if not st.session_state.interaction_timeline and isinstance(
            original_request, str
        ):
            st.session_state.interaction_timeline = [
                {"title": "需求", "content": original_request}
            ]


def _append_clarification_timeline(
    questions: Sequence[Mapping[str, Any]],
    answers: Mapping[str, Any],
) -> None:
    prompts = {
        question["field"]: question.get("question", question["field"])
        for question in questions
        if isinstance(question.get("field"), str)
    }
    lines = [
        f"{prompts.get(field, field)} → {_summary_value(value)}"
        for field, value in answers.items()
    ]
    st.session_state.interaction_timeline.append(
        {"title": "本批補充回答", "content": "\n".join(lines)}
    )


def _render_text_items(title: str, values: Any) -> None:
    if not isinstance(values, list) or not values:
        return
    st.caption(title)
    for value in values:
        st.write(f"• {_summary_value(value)}")


def _summary_value(value: Any) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    return str(value)


def _display_label(value: Any) -> str:
    return str(value).replace("_", " ") if value is not None else "—"


def _is_blank(value: Any) -> bool:
    return value == "" or value == []


def _show_api_error(error: UiApiError) -> None:
    st.error(error.user_message)
    if error.correlation_id:
        st.caption(f"Correlation ID：{error.correlation_id}")


if __name__ == "__main__":
    main()
