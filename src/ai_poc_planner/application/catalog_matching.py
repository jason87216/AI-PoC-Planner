"""Small deterministic matcher for the reviewed fixed opportunity catalog."""

from ai_poc_planner.catalog import get_opportunity_catalog
from ai_poc_planner.domain.catalog import (
    NonAiAlternativeDirection,
    OpportunityCandidate,
    OpportunityMatchInput,
    OpportunityMatchResult,
)

_KEYWORDS = {
    "enterprise_knowledge_and_professional_document_assist": (
        "knowledge",
        "document",
        "contract",
        "legal",
        "sop",
        "policy",
    ),
    "customer_service_assist": ("customer", "support", "service", "faq"),
    "document_classification_and_extraction": (
        "invoice",
        "ocr",
        "extract",
        "classification",
        "form",
    ),
    "meeting_summary_and_action_items": (
        "meeting",
        "minutes",
        "action items",
        "transcript",
    ),
    "marketing_content_assist": ("marketing", "campaign", "content", "copy"),
    "demand_forecasting": ("demand", "forecast", "inventory", "replenishment"),
    "predictive_maintenance": ("maintenance", "equipment", "failure"),
    "anomaly_and_risk_detection": (
        "anomaly",
        "fraud",
        "defect",
        "inspection",
        "transaction",
    ),
    "recruiting_process_assist": ("recruit", "resume", "candidate", "hiring"),
}


def match_opportunities(request: OpportunityMatchInput) -> OpportunityMatchResult:
    """Match explicit request signals to at most three fixed catalog entries."""

    signals = [signal.lower() for signal in request.business_problem_signals]
    ranked: list[tuple[int, int, OpportunityCandidate]] = []
    for position, entry in enumerate(get_opportunity_catalog()):
        matches = [
            signal
            for signal in signals
            if any(word in signal for word in _KEYWORDS[entry.opportunity_type.value])
        ]
        if not matches:
            continue
        guidance = [
            item
            for item in entry.conditional_guidance
            if (
                item.condition_field == "data_modality"
                and item.condition_value == request.data_modality
            )
            or (
                item.condition_field == "professional_domain"
                and item.condition_value == request.professional_domain
            )
        ]
        ranked.append(
            (
                len(matches),
                position,
                OpportunityCandidate(
                    opportunity_type=entry.opportunity_type,
                    match_strength=len(matches),
                    reasons=[f"Matched signal: {signal}" for signal in matches[:3]],
                    missing_information=entry.minimum_information_needed[:3],
                    clarification_questions=entry.clarification_questions[:3],
                    conditional_guidance=guidance,
                    case_references=entry.case_references[:2],
                ),
            )
        )
    candidates = [
        item[2] for item in sorted(ranked, key=lambda item: (-item[0], item[1]))[:3]
    ]
    alternatives: list[NonAiAlternativeDirection] = []
    joined = " ".join(signals)
    for direction, words in (
        (NonAiAlternativeDirection.RULE_BASED_AUTOMATION, ("fixed rules", "rule")),
        (
            NonAiAlternativeDirection.CONVENTIONAL_SOFTWARE,
            ("form", "workflow", "database", "integration"),
        ),
        (
            NonAiAlternativeDirection.DATA_ANALYTICS,
            ("dashboard", "trend", "statistics", "report"),
        ),
    ):
        if any(word in joined for word in words) and len(alternatives) < 2:
            alternatives.append(direction)
    return OpportunityMatchResult(
        candidates=candidates,
        clarifying_questions=[]
        if candidates
        else ["What business outcome, data modality, and human review boundary apply?"],
        non_ai_alternatives=alternatives,
    )
