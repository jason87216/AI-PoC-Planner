"""Fixed, readable input fixture for the fully offline CLI demonstration."""

from datetime import UTC, datetime
from uuid import UUID

from ai_poc_planner.application.contracts import OfflinePlanningRequest
from ai_poc_planner.domain.enums import EvidenceSourceType, ProjectStatus
from ai_poc_planner.domain.models import AnalysisProject, EvidenceReference

DEMO_PROJECT_ID = UUID("10000000-0000-0000-0000-000000000100")
DEMO_SESSION_ID = UUID("20000000-0000-0000-0000-000000000100")
DEMO_ASSESSMENT_ID = UUID("30000000-0000-0000-0000-000000000100")
DEMO_EVIDENCE_ID = UUID("40000000-0000-0000-0000-000000000100")
DEMO_TIMESTAMP = datetime(2026, 7, 19, 12, 0, tzinfo=UTC)


def build_demo_request(
    *,
    scenario: str = "high_value_low_risk",
    output_path: str | None = None,
) -> OfflinePlanningRequest:
    project = AnalysisProject(
        id=DEMO_PROJECT_ID,
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
        status=ProjectStatus.READY_FOR_ASSESSMENT,
        created_at=DEMO_TIMESTAMP,
        updated_at=DEMO_TIMESTAMP,
    )
    return OfflinePlanningRequest(
        project=project,
        session_id=DEMO_SESSION_ID,
        assessment_id=DEMO_ASSESSMENT_ID,
        evaluated_at=DEMO_TIMESTAMP,
        interview_answers={
            "scenario": scenario,
            "target_users": ["客服人員"],
            "current_workflow": "客服人員人工搜尋已核准的產品文件。",
            "data_sources": ["核准產品文件", "代表性問題集"],
            "owner": "客服流程負責人",
        },
        evidence=[
            EvidenceReference(
                id=DEMO_EVIDENCE_ID,
                project_id=DEMO_PROJECT_ID,
                session_id=DEMO_SESSION_ID,
                source_type=EvidenceSourceType.INTERVIEW,
                source_ref="interview:offline-demo:1",
                label="固定離線訪談資料",
                metadata={"fixture": "offline-demo-v1"},
            )
        ],
        output_path=output_path,
    )
