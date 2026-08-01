from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from ai_poc_planner.ui.api_client import ApiClient, ApiClientError
from ai_poc_planner.ui.results import (
    MarkdownDownload,
    analysis_overview,
    markdown_download,
    markdown_download_name,
    report_sections,
    report_synthesis_view,
    result_view_for_status,
    reviewed_case_sources,
)

PROJECT_ID = "10000000-0000-0000-0000-000000000001"


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> ApiClient:
    return ApiClient(
        client=httpx.Client(
            base_url="http://planner.test", transport=httpx.MockTransport(handler)
        )
    )


def test_results_client_uses_the_public_version_analysis_and_report_paths() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(201 if request.method == "POST" else 200, json={})

    api = _client(handler)
    api.get_project_version(PROJECT_ID, 2)
    api.create_analysis(PROJECT_ID, 2)
    api.get_analysis(PROJECT_ID, 2)
    api.create_report(PROJECT_ID, 2)
    api.get_report(PROJECT_ID, 2)

    assert [(item.method, item.url.path) for item in requests] == [
        ("GET", f"/v1/projects/{PROJECT_ID}/versions/2"),
        ("POST", f"/v1/projects/{PROJECT_ID}/versions/2/analysis"),
        ("GET", f"/v1/projects/{PROJECT_ID}/versions/2/analysis"),
        ("POST", f"/v1/projects/{PROJECT_ID}/versions/2/report"),
        ("GET", f"/v1/projects/{PROJECT_ID}/versions/2/report"),
    ]


@pytest.mark.parametrize(
    ("status", "view"),
    [
        ("ready_for_assessment", "ready"),
        ("assessed", "assessed"),
        ("complete", "complete"),
        ("interviewing", "unavailable"),
    ],
)
def test_persisted_project_status_alone_controls_result_view(
    status: str, view: str
) -> None:
    assert result_view_for_status(status) == view


def test_analysis_presentation_keeps_required_business_content_without_ids() -> None:
    view = analysis_overview(
        {
            "id": "internal-analysis-id",
            "requirement_summary": "Route invoices with human review.",
            "conclusion": "conditional_proceed",
            "conclusion_rationale": "Start with a limited workflow.",
            "weighted_total": 72.5,
            "gate_disposition": "review_required",
            "recommended_option_key": "option-a",
            "options": [
                {
                    "option_key": "option-a",
                    "title": "Human-assisted routing",
                    "summary": "Classify then review.",
                    "expected_benefits": ["Faster routing"],
                    "limitations": ["Needs sampling"],
                    "prerequisites": ["Confirm owners"],
                    "risks": ["Misclassification"],
                    "decision_authority": "human",
                    "processing_boundary": "assistive_only",
                    "human_review_points": ["Approve edge cases"],
                }
            ],
            "scores": [
                {
                    "dimension": "data_readiness",
                    "rating": 3,
                    "weight": 0.2,
                    "weighted_points": 0.6,
                    "rationale": "Examples are available.",
                    "data_gaps": ["Volume unknown"],
                    "risks": ["Coverage"],
                    "improvement_conditions": ["Sample records"],
                }
            ],
            "gate_results": [
                {
                    "rule_id": "gate-01",
                    "disposition": "review_required",
                    "reason": "Approval remains human.",
                    "required_controls": ["Human approval"],
                    "human_review_required": "yes",
                }
            ],
            "overall_risks": ["Coverage"],
            "unresolved_gaps": ["Volume"],
        }
    )

    assert view["weighted_total"] == 72.5
    assert view["options"][0]["recommended"] is True
    assert view["scores"][0]["data_gaps"] == ["Volume unknown"]
    assert view["gates"][0]["required_controls"] == ["Human approval"]
    assert "internal-analysis-id" not in str(view)
    assert "option-a" not in str(view)
    assert "gate-01" not in str(view)


def test_report_sections_cases_and_markdown_filename_use_persisted_content() -> None:
    report = {
        "report": {
            "executive_summary": {"content": "Summary."},
            "open_issues_and_next_actions": {"content": "Next."},
        },
        "markdown": (
            "# AI PoC Planning Report\n\n## Relevant Reviewed Cases\n\n"
            "- Example Org (B): Example Source — https://example.test/case\n\n"
            "## Fact-Backed Scoring Appendix\n"
        ),
    }

    assert [section["title"] for section in report_sections(report)] == [
        "執行摘要",
        "待釐清事項與下一步",
    ]
    assert reviewed_case_sources(report["markdown"]) == [
        {
            "organization": "Example Org",
            "evidence_grade": "B",
            "source_name": "Example Source",
            "source_url": "https://example.test/case",
        }
    ]
    assert (
        markdown_download_name("Invoice / triage", 2)
        == "AI-PoC-Plan-Invoice-triage-v2.md"
    )


def test_markdown_download_uses_the_persisted_report_transformation() -> None:
    report = {"markdown": "# 已保存報告\n\n內容。\n"}

    download = markdown_download(report, "權限申請 / PoC", 3)

    assert isinstance(download, MarkdownDownload)
    assert download.data == report["markdown"].encode("utf-8")
    assert download.data.decode("utf-8") == report["markdown"]
    assert download.file_name == "AI-PoC-Plan-權限申請-PoC-v3.md"
    assert download.mime == "text/markdown"


def test_result_errors_are_mapped_to_safe_user_messages() -> None:
    api = _client(
        lambda _: httpx.Response(
            409,
            json={
                "error": {
                    "code": "report_not_ready",
                    "message": "raw response at http://internal.test/secret",
                }
            },
        )
    )

    with pytest.raises(ApiClientError) as caught:
        api.create_report(PROJECT_ID, 1)

    assert caught.value.code == "report_not_ready"
    assert "internal.test" not in caught.value.user_message
    assert "secret" not in caught.value.user_message


def test_results_ui_does_not_expose_internal_details_or_forbidden_layers() -> None:
    root = Path(__file__).parents[2]
    source = "\n".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in ["app_pages/results.py", "src/ai_poc_planner/ui/results.py"]
    )

    assert "ai_poc_planner.application" not in source
    assert "ai_poc_planner.persistence" not in source
    assert "ai_poc_planner.providers" not in source
    assert "st.json" not in source
    assert "base_url" not in source
    assert "traceback" not in source.casefold()
    assert source.count("st.expander") == 1
    assert "report_synthesis_view" in source
    assert "case_evidence" in source
    assert "case_support_summaries" in source
    assert "implementation_references" in source
    assert "source_url" in source


def test_report_synthesis_view_keeps_only_the_redesigned_article_fields() -> None:
    view = report_synthesis_view(
        {
            "synthesis": {
                "schema_version": "2.2",
                "executive_narrative": "先顯示結論。",
                "recommended_solution": {
                    "display_name_zh": "權限申請標準化、規則檢查與人工核准",
                    "short_description_zh": "以固定規則檢查申請內容。",
                    "detailed_description_zh": "先整理申請格式，再由主管核准。",
                    "suitable_when_zh": "規則與責任可以明確界定時。",
                    "not_suitable_when_zh": "規則尚未釐清時。",
                    "typical_scope_zh": "申請表、規則清單與核准紀錄。",
                    "human_boundary_zh": "主管保留最終核准。",
                    "expected_outputs_zh": "規則結果與核准紀錄。",
                    "acceptance_focus_zh": "檢查漏項與例外處理。",
                    "solution_key": "hidden-solution-key",
                },
                "reviewed_cases": [
                    {
                        "display_title_zh": "Morgan Stanley：企業知識檢索與人工覆核",
                        "organization": "Morgan Stanley",
                        "case_summary_zh": "案例摘要。",
                        "problem_context_zh": "需要從文件中查找資訊。",
                        "implemented_approach_zh": "使用檢索與人工覆核。",
                        "documented_outcomes_zh": "來源記錄採用與查找效率改善。",
                        "transferable_practices_zh": "建立評估集與人工修訂。",
                        "limitations_zh": "責任與部署環境不同。",
                        "source_name": "OpenAI 客戶案例：Morgan Stanley",
                        "source_url": "https://example.test/morgan",
                        "case_id": "hidden-case-id",
                    }
                ],
                "case_support_summaries": [
                    {
                        "case_title": "Morgan Stanley：企業知識檢索與人工覆核",
                        "supported_practices": "人工覆核。",
                        "project_adoption": "本專案先保留人工確認。",
                    }
                ],
                "implementation_references": [
                    {
                        "topic": "流程實施",
                        "display_title_zh": "官方文件",
                        "purpose_zh": "說明流程責任。",
                        "source_name": "官方文件來源",
                        "source_url": "https://example.test/reference",
                    }
                ],
                "interview_findings": [
                    {
                        "topic": "人工責任",
                        "confirmed_content": "主管最終核准。",
                        "assessment_impact": "限制自動化範圍。",
                        "source_question": "誰最終核准？",
                        "question_uuid": "hidden-question-id",
                    }
                ],
                "comparison_narrative": "先說明比較範圍。\n\n再說明案例限制。",
                "current_target_comparison": [
                    {
                        "aspect": "人工責任",
                        "current_state": "主管最終核准。",
                        "target_state": "AI 提供草稿，主管確認。",
                        "main_gap": "覆核流程待確認。",
                        "treatment": "保留確認步驟。",
                    }
                ],
                "option_comparison": [
                    {
                        "option": "AI 檢索與人工確認",
                        "positioning": "先檢索核准內容，再由人員確認。",
                        "supporting_cases": ["Morgan Stanley：知識檢索與人工修訂"],
                        "case_evidence": "案例支持檢索與人工修訂。",
                        "transferable_practice": "保留來源與修改紀錄。",
                        "cannot_copy": ["不可照搬自動化程度。"],
                        "conclusion": "正式推薦。",
                        "recommended": True,
                        "option_key": "hidden-option-id",
                    },
                    {
                        "option": "規則與流程標準化",
                        "positioning": "以固定規則檢查。",
                        "supporting_cases": [],
                        "case_evidence": "本次未找到可直接參照的已審核案例。",
                        "transferable_practice": "保留人工確認。",
                        "cannot_copy": [],
                        "conclusion": "比較基線。",
                        "recommended": False,
                    },
                ],
                "recommendation_narrative": "完整推薦理由。",
                "implementation_roadmap": [
                    {
                        "phase": "準備階段（立即行動）",
                        "actions": ["整理核准資料。"],
                        "outputs": ["測試樣本。"],
                        "human_decision_boundary": "人員確認。",
                        "acceptance_criteria": ["可追溯。"],
                    }
                ],
                "major_risks_and_boundaries": ["不自動對外發送。"],
                "appendix": {
                    "scores": [],
                    "hard_gates": [],
                    "safe_interview_qa": [],
                    "evidence_basis": [],
                    "fact_key": "hidden-fact-key",
                },
            }
        }
    )

    assert view["executive_narrative"] == "先顯示結論。"
    assert view["interview_findings"][0]["confirmed_content"] == "主管最終核准。"
    assert view["comparison_narrative"].startswith("先說明")
    assert view["option_comparison"][0]["supporting_cases"] == [
        "Morgan Stanley：知識檢索與人工修訂"
    ]
    assert [item["recommended"] for item in view["option_comparison"]] == [
        True,
        False,
    ]
    assert view["recommended_solution"]["display_name_zh"] == (
        "權限申請標準化、規則檢查與人工核准"
    )
    assert view["reviewed_cases"][0]["source_name"] == "OpenAI 客戶案例：Morgan Stanley"
    assert view["reviewed_cases"][0]["source_url"] == "https://example.test/morgan"
    assert view["case_support_summaries"][0]["case_title"].startswith("Morgan Stanley")
    assert view["implementation_references"][0]["source_url"] == (
        "https://example.test/reference"
    )
    assert "question_uuid" not in repr(view)
    assert "hidden-question-id" not in repr(view)
    assert "hidden-option-id" not in repr(view)
    assert "fact_key" not in repr(view)
    assert "source_question" not in repr(view)
    assert "hidden-solution-key" not in repr(view)
    assert "hidden-case-id" not in repr(view)
    assert "safe_interview_qa" not in repr(view)
    assert "evidence_basis" not in repr(view)
