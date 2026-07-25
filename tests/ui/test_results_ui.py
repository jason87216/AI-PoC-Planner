from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from ai_poc_planner.ui.api_client import ApiClient, ApiClientError
from ai_poc_planner.ui.results import (
    analysis_overview,
    markdown_download_name,
    report_sections,
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
