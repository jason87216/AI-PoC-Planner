"""Deterministic case value, project fit, gaps, and phased-path composition."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from ai_poc_planner.assessment.gates import evaluate_hard_gates
from ai_poc_planner.assessment.scoring import calculate_weighted_score, score_dimensions
from ai_poc_planner.domain.analysis import ProgramGateResult, ProgramScore
from ai_poc_planner.domain.case_centered import (
    CaseCenteredAssessment,
    CaseGapAnalysis,
    CaseReferenceValue,
    CaseReferenceValueLevel,
    FitDimension,
    FitDimensionStatus,
    FitLevel,
    HardGateImpact,
    ImplementationPhase,
    MatchedCaseAssessment,
    ProjectCaseFit,
    RecommendationCategory,
    TransferablePractice,
)
from ai_poc_planner.domain.enums import (
    DataBoundary,
    DecisionAuthority,
    DigitizationLevel,
    FactStatus,
    HighImpactDomain,
    ProcessingBoundary,
)
from ai_poc_planner.domain.facts import (
    ArchitectureControllabilityFacts,
    AssessmentFacts,
    BusinessValueFacts,
    DataReadinessFacts,
    GateFacts,
    GovernanceReadinessFacts,
    TechnicalFitFacts,
    UserAdoptionFacts,
)
from ai_poc_planner.domain.models import SCORE_WEIGHTS
from ai_poc_planner.domain.project_history import FactRevision
from ai_poc_planner.domain.reviewed_cases import (
    ReviewedCase,
    ReviewedEvidenceGrade,
    ReviewStatus,
)

_GRADE_POINTS = {
    ReviewedEvidenceGrade.A.value: 30,
    ReviewedEvidenceGrade.B.value: 24,
    ReviewedEvidenceGrade.C.value: 18,
    ReviewedEvidenceGrade.D.value: 10,
}
_STOP_WORDS = {
    "and",
    "the",
    "with",
    "from",
    "for",
    "into",
    "this",
    "that",
    "需要",
    "目前",
    "以及",
    "案例",
}
_TRANSLATIONS = {
    "主管": "manager",
    "審核": "review approval",
    "核准": "approval",
    "權限": "permission access",
    "申請": "request",
    "員工": "employee",
    "職位": "role",
    "資料": "data",
    "集中式": "centralized",
    "自動": "automatic autonomous",
    "人工": "human manual",
    "流程": "workflow",
}

_MATCHING_FACT_KEYS = {
    "current_workflow_problem",
    "current_workflow",
    "desired_outcome",
    "available_data",
    "users_and_owners",
    "known_constraints",
    "workflow_scope",
    "system_dependencies",
    "governance_conditions",
    "decision_authority",
    "human_final_decision",
    "processing_boundary",
    "data_boundary",
}

_CASE_TAG_LABELS = {
    "autonomous_action": "不得自主執行高風險動作",
    "assistive_only": "僅限人工輔助",
    "human_review": "保留人工覆核",
}

_GATE_CONDITION_LABELS = {
    "obtain documented authorization and lawful basis": "取得書面授權與合法依據",
    "assign an accountable owner": "指定可追責的負責人",
    "remove autonomous final decisions and enterprise actions": (
        "移除自主最終決策與企業系統執行"
    ),
    "complete qualified professional review": "完成合格專業人工覆核",
    "remove autonomous final-decision authority": "移除自主最終決策權限",
    "require a qualified human final decision": "要求合格人員做最終決策",
    "preserve a meaningful human final decision": "保留有實質意義的人員最終決策",
    "provide a contest or review path": "提供申訴或覆核途徑",
    "approve governance controls": "核准治理控制措施",
    "enable audit controls": "啟用稽核控制措施",
    "use an approved local or private endpoint": "使用核准的本機或私有端點",
    "define data minimization": "定義資料最小化措施",
    "define retention and deletion controls": "定義保存與刪除控制措施",
    "enforce least-privilege access control": "強制執行最小權限存取控制",
    "approve required security controls": "核准必要的安全控制措施",
    "approve required governance controls": "核准必要的治理控制措施",
    "enable required audit controls": "啟用必要的稽核控制措施",
    "make required data available": "提供必要資料",
    "digitize or OCR source material": "將來源資料數位化或進行 OCR 擷取",
    "create a representative validation sample": "建立具代表性的驗證樣本",
}


def _case_tag_label(value: str) -> str:
    return _CASE_TAG_LABELS.get(value, value)


def _gate_condition_label(value: str) -> str:
    return _GATE_CONDITION_LABELS.get(value, value)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(item) for item in value)
    return str(value)


def _terms(value: object) -> set[str]:
    text = _text(value).casefold()
    for source, replacement in _TRANSLATIONS.items():
        text = text.replace(source, f" {replacement} ")
    return {
        token
        for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", text)
        if token not in _STOP_WORDS and len(token) > 1
    }


def _fact_map(facts: Iterable[FactRevision]) -> dict[str, tuple[FactStatus, object]]:
    """Use only the stable fact keys allowed to participate in matching."""

    result: dict[str, tuple[FactStatus, object]] = {}
    for fact in facts:
        key = fact.fact_key.strip().casefold()
        if key in _MATCHING_FACT_KEYS:
            result[key] = (fact.status, fact.value)
    return result


def _all_fact_map(facts: Iterable[FactRevision]) -> dict[str, FactRevision]:
    return {fact.fact_key.strip().casefold(): fact for fact in facts}


def _confirmed_text(facts: Mapping[str, FactRevision]) -> str:
    return " ".join(
        _text(fact.value)
        for fact in facts.values()
        if fact.status is FactStatus.CONFIRMED
    ).casefold()


def _confirmed(facts: Mapping[str, FactRevision], *keys: str) -> bool:
    return any(
        key in facts and facts[key].status is FactStatus.CONFIRMED for key in keys
    )


def _contains(facts: Mapping[str, FactRevision], *words: str) -> bool:
    text = _confirmed_text(facts)
    return any(word.casefold() in text for word in words)


def _contains_positive(facts: Mapping[str, FactRevision], *words: str) -> bool:
    """Find a positive signal within one fact and sentence.

    A project can have one confirmed fact saying that images exist and another
    sentence saying that no validation sample exists.  Joining all facts before
    checking negation makes those two statements contaminate each other.
    """

    negation_markers = (
        "not available",
        "without",
        "沒有",
        "尚未",
        "不需要",
        "無法",
        "缺少",
        "不足",
        "無",
        "計畫",
        "計劃",
        "預計",
        "未來",
        "將",
        "需要",
        "no",
        "not",
    )
    contrast_markers = ("但", "可是", "然而", "but", "however")

    def is_negated(sentence: str, start: int, end: int) -> bool:
        before = sentence[max(0, start - 24) : start]
        after = sentence[end : min(len(sentence), end + 24)]
        marker_positions = [
            (before.rfind(marker), marker) for marker in negation_markers
        ]
        marker_positions = [item for item in marker_positions if item[0] >= 0]
        if marker_positions:
            marker_start, marker = max(marker_positions)
            trailing = before[marker_start + len(marker) :]
            if not any(contrast in trailing for contrast in contrast_markers):
                return True
        return bool(
            re.match(
                r"\s*(?:[a-z]+\s+){0,4}(?:not\s+available|not\b|unavailable|無法|不存在|缺少|不足)",
                after,
            )
        )

    for fact in facts.values():
        if fact.status is not FactStatus.CONFIRMED:
            continue
        for sentence in re.split(r"[。！？!?；;\n]", _text(fact.value).casefold()):
            for word in words:
                for match in re.finditer(re.escape(word.casefold()), sentence):
                    if not is_negated(sentence, match.start(), match.end()):
                        return True
    return False


_RULES_FIRST_SIGNAL_WORDS = (
    "rule-based",
    "規則優先",
    "表單流程",
    "規則引擎",
    "條件判斷",
    "結構化表單",
    "表單驗證",
    "傳統自動化",
    "不需要複雜自然語言",
    "不需要自然語言",
)

_PERMISSION_REQUEST_SIGNAL_WORDS = (
    "權限申請",
    "存取申請",
    "permission request",
    "access request",
)

_PERMISSION_RULE_SIGNAL_WORDS = (
    "規則檢查",
    "規則判斷",
    "權限規則",
    "權限範本",
    "固定規則",
    "必填欄位",
    "漏填",
    "rule check",
    "rule validation",
)

_PERMISSION_HUMAN_APPROVAL_SIGNAL_WORDS = (
    "主管核准",
    "主管審核",
    "人工核准",
    "人工審核",
    "人工審批",
    "最終核准",
    "human approval",
    "human review",
)


_EMPLOYMENT_HIGH_IMPACT_PATTERNS = (
    r"招募|招聘|錄用|录用|雇用|聘用|解雇|解僱|終止雇傭|终止雇佣|升遷|升迁|晉升|晋升",
    r"薪酬|薪資|薪资|績效|绩效|處分|处分|任職資格|任职资格",
    r"高風險.{0,8}(?:系統)?權限",
    r"(?:employment|hiring|recruiting|termination|promotion|compensation|performance|disciplinary|qualification)",
    r"high[- ]risk.{0,12}(?:system )?permission.{0,12}(?:approval|approve|authorize)",
)


def _has_employment_high_impact_signal(
    facts: Mapping[str, FactRevision],
) -> bool:
    for fact in facts.values():
        if fact.status is not FactStatus.CONFIRMED:
            continue
        text = _text(fact.value).casefold()
        if fact.fact_key.casefold() in {"high_impact_domain", "decision_impact"}:
            if any(term in text for term in ("employment", "人事", "高影響")):
                return True
        if any(
            re.search(pattern, text) for pattern in _EMPLOYMENT_HIGH_IMPACT_PATTERNS
        ):
            return True
    return False


def _is_controlled_permission_request_workflow(
    facts: Mapping[str, FactRevision],
) -> bool:
    """Recognise an access-request workflow without relying on a provider option.

    The route requires the request, deterministic rule checking, and a named
    human approval boundary together.  A generic mention of access or a
    knowledge article about permissions is therefore insufficient.
    """

    return (
        _contains(facts, *_PERMISSION_REQUEST_SIGNAL_WORDS)
        and _contains(facts, *_PERMISSION_RULE_SIGNAL_WORDS)
        and _contains(facts, *_PERMISSION_HUMAN_APPROVAL_SIGNAL_WORDS)
    )


def build_deterministic_assessment_facts(
    facts: Iterable[FactRevision],
    *,
    selected_authority: DecisionAuthority = DecisionAuthority.HUMAN_FINAL_DECISION,
    selected_boundary: ProcessingBoundary = ProcessingBoundary.LOCAL_ONLY,
) -> AssessmentFacts:
    """Map confirmed discovery facts to the existing deterministic rubric inputs."""

    by_key = _all_fact_map(facts)
    confirmed_ids = [
        fact.id for fact in by_key.values() if fact.status is FactStatus.CONFIRMED
    ]
    has_owner = _confirmed(by_key, "users_and_owners", "process_owner", "owner")
    data_text = " ".join(
        _text(fact.value)
        for key, fact in by_key.items()
        if key in {"available_data", "data_sources"}
        and fact.status is FactStatus.CONFIRMED
    ).casefold()
    has_data = _confirmed(by_key, "available_data", "data_sources") and not any(
        marker in data_text
        for marker in ("none", "not available", "沒有資料", "無資料", "尚無資料")
    )
    digitization = (
        DigitizationLevel.COMPLETE
        if _contains(by_key, "structured", "database", "excel", "標準化")
        else DigitizationLevel.PARTIAL
        if has_data
        else DigitizationLevel.NONE
    )
    integration_signal = _contains(by_key, "api", "integration", "整合")
    high_risk_integration_signal = _contains(by_key, "write", "寫入", "自動執行")
    evidence = confirmed_ids
    return AssessmentFacts(
        business_value=BusinessValueFacts(
            evidence_ids=evidence,
            pain_defined=_confirmed(
                by_key, "current_workflow_problem", "current_workflow"
            ),
            beneficiary_defined=_confirmed(by_key, "users_and_owners", "target_users"),
            owner_identified=has_owner,
            owner_approved=_contains(by_key, "approved", "核准", "同意"),
            quantitative_baseline=_contains(by_key, "baseline", "基準", "目前數值"),
            target_kpi_defined=_contains(by_key, "kpi", "metric", "指標"),
            benefit_assumptions_documented=_confirmed(by_key, "desired_outcome"),
            cost_baseline_available=_contains(by_key, "cost", "費用", "成本"),
            roi_formula_available=_contains(by_key, "roi", "回報公式"),
        ),
        data_readiness=DataReadinessFacts(
            evidence_ids=evidence,
            data_available=has_data,
            lawful_access=_contains(by_key, "lawful", "authorized", "合法", "授權"),
            digitization=digitization,
            quality_known=_contains(by_key, "quality", "品質", "資料品質"),
            quality_sampled=_contains(by_key, "sample", "抽樣", "樣本"),
            quality_measured=_contains(by_key, "measured", "量測", "衡量"),
            validation_sample_available=_contains_positive(
                by_key, "validation", "驗證集", "驗證樣本"
            ),
            representative_validation_sample=_contains(
                by_key, "representative", "代表性"
            ),
            gaps_resolvable_in_poc=has_data,
        ),
        technical_fit=TechnicalFitFacts(
            evidence_ids=evidence,
            ai_needed=not _contains(
                by_key,
                "rule only",
                "不需要 ai",
                "不需 ai",
                "不需要複雜自然語言",
                "不需要自然語言",
            ),
            technically_feasible=not _contains(by_key, "not feasible", "不可行"),
            traditional_solution_preferred=_contains(
                by_key, *_RULES_FIRST_SIGNAL_WORDS
            ),
            technical_path_defined=_contains(
                by_key, "api", "integration", "整合", "架構"
            ),
            retrieval_required=_contains(by_key, "knowledge", "search", "檢索", "知識"),
            reasoning_required=_contains(by_key, "reasoning", "判斷", "推理"),
            tool_collaboration_required=_contains(by_key, "tool", "工具", "系統操作"),
            boundaries_defined=_confirmed(
                by_key, "known_constraints", "processing_boundary"
            ),
            key_assumptions_testable=has_data,
        ),
        architecture_controllability=ArchitectureControllabilityFacts(
            evidence_ids=evidence,
            integration_count=int(integration_signal or high_risk_integration_signal),
            high_risk_integration_count=int(high_risk_integration_signal),
            unknown_dependency_count=1
            if not _confirmed(by_key, "known_constraints")
            else 0,
            interfaces_known=_contains(by_key, "api", "interface", "介面"),
            test_environment_available=_contains(by_key, "test", "測試環境", "sandbox"),
            mocks_available=_contains(by_key, "mock", "模擬"),
            data_boundary_defined=_confirmed(
                by_key, "data_boundary", "processing_boundary", "known_constraints"
            ),
            dependencies_replaceable=_contains(by_key, "replaceable", "可替換"),
            observability_available=_contains(by_key, "audit", "log", "紀錄", "稽核"),
            reproducible_environment=_contains(by_key, "reproducible", "可重現"),
        ),
        governance_readiness=GovernanceReadinessFacts(
            evidence_ids=evidence,
            lawful_basis_confirmed=_contains(by_key, "lawful", "合法", "授權"),
            accountable_owner_confirmed=has_owner,
            data_boundary_defined=_confirmed(
                by_key, "data_boundary", "processing_boundary", "known_constraints"
            ),
            data_types_identified=_confirmed(by_key, "available_data"),
            risks_identified=_confirmed(by_key, "known_constraints"),
            controls_identified=_contains(by_key, "control", "控制", "least privilege"),
            policy_defined=_contains(by_key, "policy", "政策", "規範"),
            reviewer_identified=_contains(by_key, "reviewer", "review", "主管", "審核"),
            minimization_defined=_contains(by_key, "minimization", "最小化"),
            retention_defined=_contains(by_key, "retention", "保留期限"),
            approved_policy=_contains(by_key, "approved policy", "核准政策"),
            formal_risk_assessment=_contains(by_key, "risk assessment", "風險評估"),
            audit_records_available=_contains(by_key, "audit", "稽核紀錄"),
            incident_process_defined=_contains(by_key, "incident", "事件處理"),
        ),
        user_adoption=UserAdoptionFacts(
            evidence_ids=evidence,
            users_opposed=_contains(by_key, "opposed", "反對"),
            process_owner_confirmed=has_owner,
            affected_roles_involved=_confirmed(by_key, "users_and_owners"),
            value_proposition_clear=_confirmed(by_key, "desired_outcome"),
            representative_users_committed=_contains(
                by_key, "committed", "願意", "承諾"
            ),
            workflow_adjusted=_contains(by_key, "workflow", "流程調整"),
            training_plan_defined=_contains(by_key, "training", "訓練"),
            feedback_process_defined=_contains(by_key, "feedback", "回饋"),
            users_co_designed=_contains(by_key, "co-design", "共同設計"),
            adoption_metrics_defined=_contains(by_key, "adoption metric", "採用指標"),
            support_owner_confirmed=_contains(by_key, "support owner", "支援負責人"),
            iteration_owner_confirmed=_contains(
                by_key, "iteration owner", "迭代負責人"
            ),
        ),
        gates=GateFacts(
            evidence_ids=evidence,
            authorization_confirmed=_contains(by_key, "authorized", "授權", "核准"),
            lawful_basis_confirmed=_contains(by_key, "lawful", "合法"),
            accountable_owner_confirmed=has_owner,
            prohibited_use=_contains(by_key, "prohibited", "禁止用途"),
            high_impact_domain=(
                HighImpactDomain.EMPLOYMENT
                if _has_employment_high_impact_signal(by_key)
                else HighImpactDomain.NONE
            ),
            autonomous_final_decision=selected_authority
            is DecisionAuthority.AUTONOMOUS_ACTION,
            autonomous_enterprise_action=selected_authority
            is DecisionAuthority.AUTONOMOUS_ACTION,
            meaningful_human_review=selected_authority
            is not DecisionAuthority.AUTONOMOUS_ACTION,
            contest_or_review_path=_contains(
                by_key, "contest", "appeal", "申訴", "覆核"
            ),
            personal_data=_contains(by_key, "personal", "employee", "員工", "個資"),
            sensitive_data=_contains(by_key, "sensitive", "敏感"),
            minimization_control=_contains(by_key, "minimization", "最小化"),
            retention_control=_contains(by_key, "retention", "保留期限"),
            access_control=_contains(
                by_key, "access control", "存取控制", "least privilege"
            ),
            security_controls_confirmed=_contains(by_key, "security", "安全控制"),
            security_controls_required=True,
            governance_controls_confirmed=_contains(by_key, "governance", "治理"),
            governance_controls_required=True,
            audit_controls_confirmed=_contains(by_key, "audit", "稽核紀錄"),
            audit_controls_required=True,
            data_boundary=(
                DataBoundary.LOCAL_ONLY
                if selected_boundary is ProcessingBoundary.LOCAL_ONLY
                else DataBoundary.PRIVATE_ENDPOINT
                if selected_boundary is ProcessingBoundary.PRIVATE_ENDPOINT
                else DataBoundary.EXTERNAL_ALLOWED
            ),
            external_endpoint_requested=selected_boundary
            is ProcessingBoundary.EXTERNAL_ENDPOINT,
            data_available=has_data,
            digitization=digitization,
            validation_sample_available=_contains_positive(
                by_key, "validation", "驗證集", "驗證樣本"
            ),
        ),
    )


def build_deterministic_scores(
    facts: Iterable[FactRevision], tokens: Mapping[str, object]
) -> tuple[list[ProgramScore], int]:
    revisions = tuple(facts)
    assessment_facts = build_deterministic_assessment_facts(revisions)
    results = score_dimensions(assessment_facts)
    by_id = {str(fact.id): fact for fact in revisions}
    unknown_refs = sorted(
        token
        for token, fact_id in tokens.items()
        if by_id[str(fact_id)].status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    )
    confirmed_refs = sorted(
        token
        for token, fact_id in tokens.items()
        if by_id[str(fact_id)].status is FactStatus.CONFIRMED
    )
    unknown_keys = [
        fact.fact_key
        for fact in revisions
        if fact.status in {FactStatus.UNKNOWN, FactStatus.MISSING}
    ]
    scores: list[ProgramScore] = []
    for item in results:
        gaps = [f"尚未確認：{key}" for key in unknown_keys]
        scores.append(
            ProgramScore(
                dimension=item.dimension,
                rating=item.rating,
                weight=SCORE_WEIGHTS[item.dimension],
                weighted_points=int(item.weighted_points),
                rationale=(
                    "評價對象：目前專案在現階段採用實施路徑的可行性與準備程度。"
                    f"主要依據：{item.rationale}"
                ),
                evidence_fact_refs=confirmed_refs or ["F001"],
                gap_fact_refs=unknown_refs,
                data_gaps=gaps,
                risks=["未知條件若未補足，不能擴大自動化範圍。"]
                if unknown_keys
                else [],
                improvement_conditions=(
                    ["補足列出的未知條件並重新驗證。"] if item.rating < 5 else []
                ),
                unknown_fact_refs=unknown_refs,
                unknown_impact=(
                    "未知資料以保守方式拉低準備度，需先確認。"
                    if unknown_keys
                    else "本項沒有未確認資料。"
                ),
            )
        )
    return scores, calculate_weighted_score(
        [
            item.model_copy(update={"weighted_points": float(item.weighted_points)})
            for item in results
        ]
    )


def build_deterministic_gate_evaluation(
    facts: Iterable[FactRevision],
    *,
    selected_authority: DecisionAuthority,
    selected_boundary: ProcessingBoundary,
):
    assessment_facts = build_deterministic_assessment_facts(
        facts,
        selected_authority=selected_authority,
        selected_boundary=selected_boundary,
    )
    return evaluate_hard_gates(assessment_facts.gates)


def infer_opportunity_types(facts: Iterable[FactRevision]) -> tuple[object, ...]:
    """Infer catalog types from confirmed facts with a fixed keyword table."""

    from ai_poc_planner.application.catalog_matching import match_opportunities
    from ai_poc_planner.domain.catalog import OpportunityMatchInput, OpportunityType

    facts_tuple = tuple(facts)
    by_key = _all_fact_map(facts_tuple)
    if _contains(by_key, *_RULES_FIRST_SIGNAL_WORDS):
        return ()
    signals = [
        _text(fact.value)
        for fact in facts_tuple
        if fact.status is FactStatus.CONFIRMED
        and fact.fact_key.strip().casefold() in _MATCHING_FACT_KEYS
        and _text(fact.value).strip()
    ]
    if not signals:
        return ()
    text = " ".join(signals).casefold()
    project_keywords = {
        OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST: (
            "文件",
            "合約",
            "權限",
            "知識",
            "規範",
            "policy",
            "document",
        ),
        OpportunityType.CUSTOMER_SERVICE_ASSIST: ("客服", "客戶", "問答", "faq"),
        OpportunityType.DOCUMENT_CLASSIFICATION_AND_EXTRACTION: (
            "發票",
            "ocr",
            "分類",
            "擷取",
            "extract",
        ),
        OpportunityType.MEETING_SUMMARY_AND_ACTION_ITEMS: (
            "會議",
            "逐字稿",
            "meeting",
        ),
        OpportunityType.MARKETING_CONTENT_ASSIST: ("行銷", "文案", "marketing"),
        OpportunityType.DEMAND_FORECASTING: ("庫存", "補貨", "需求預測", "forecast"),
        OpportunityType.PREDICTIVE_MAINTENANCE: (
            "設備",
            "故障",
            "維修",
            "maintenance",
        ),
        OpportunityType.ANOMALY_AND_RISK_DETECTION: (
            "詐欺",
            "異常",
            "檢測",
            "fraud",
        ),
        OpportunityType.RECRUITING_PROCESS_ASSIST: (
            "招募",
            "履歷",
            "候選",
            "recruit",
        ),
    }
    inferred = tuple(
        opportunity
        for opportunity, keywords in project_keywords.items()
        if any(keyword.casefold() in text for keyword in keywords)
    )
    if inferred:
        return inferred[:3]
    result = match_opportunities(
        OpportunityMatchInput(business_problem_signals=signals)
    )
    return tuple(item.opportunity_type for item in result.candidates)


def _project_text(
    facts: Mapping[str, tuple[FactStatus, object]], keys: Sequence[str]
) -> str:
    return " ".join(
        _text(value)
        for key in keys
        if key in facts and facts[key][0] is FactStatus.CONFIRMED
        for value in (facts[key][1],)
    )


def calculate_case_reference_value(case: ReviewedCase) -> CaseReferenceValue:
    """Calculate the reference value of a reviewed case, independent of fit.

    The score is a transparent evidence heuristic: review status (25), evidence
    grade (30), source traceability (10), outcome evidence (20), documented
    limitations (5), and context completeness (10). Missing facts reduce the
    score and are reported as unknown rather than treated as positive evidence.
    """

    basis: list[str] = []
    unknown: list[str] = []
    score = 0
    if case.review_status is ReviewStatus.APPROVED:
        score += 25
        basis.append("案例已通過審核")
    else:
        unknown.append("案例尚未通過正式審核")
    grade_points = _GRADE_POINTS.get(case.evidence_grade.value, 0)
    score += grade_points
    basis.append(f"證據等級為 {case.evidence_grade.value}")
    if case.source_references:
        score += 10
        basis.append("有可追溯來源")
    else:
        unknown.append("來源參照未完整記錄")
    outcomes = case.measurable_outcomes or case.reported_outcomes
    if outcomes:
        score += 20
        basis.append("有記錄成果或結果")
    else:
        unknown.append("缺少成果證據")
    if case.risks_or_limitations:
        score += 5
        basis.append("限制已被記錄")
    else:
        unknown.append("限制未記錄")
    context_fields = (
        case.organization_type,
        case.workflow_scope,
        case.solution_pattern,
        case.decision_authority,
        case.processing_boundary,
        case.implementation_stage,
    )
    context_count = sum(bool(item) for item in context_fields)
    if context_count == len(context_fields):
        score += 10
        basis.append("情境、邊界與實施階段描述完整")
    else:
        if context_count:
            score += 5
        unknown.append("情境或實施邊界仍有未記錄欄位")

    if score >= 75:
        level = CaseReferenceValueLevel.HIGH
    elif score >= 50:
        level = CaseReferenceValueLevel.MEDIUM
    elif score > 0:
        level = CaseReferenceValueLevel.LOW
    else:
        level = CaseReferenceValueLevel.INSUFFICIENT_EVIDENCE
    return CaseReferenceValue(
        level=level, score=min(score, 100), basis=basis, unknown_items=unknown
    )


def _dimension(
    name: str,
    project_text: str,
    case_text: str | None,
    *,
    unknown_reason: str,
    similar_reason: str,
    different_reason: str,
) -> FitDimension:
    if not project_text or not case_text:
        return FitDimension(
            name=name,
            status=FitDimensionStatus.UNKNOWN,
            score=50,
            basis=[unknown_reason],
        )
    overlap = _terms(project_text) & _terms(case_text)
    if overlap:
        return FitDimension(
            name=name,
            status=FitDimensionStatus.SIMILAR,
            score=100,
            basis=[similar_reason],
        )
    return FitDimension(
        name=name,
        status=FitDimensionStatus.DIFFERENT,
        score=20,
        basis=[different_reason],
    )


def calculate_project_case_fit(
    facts: Iterable[FactRevision], case: ReviewedCase
) -> ProjectCaseFit:
    """Compare confirmed project facts with explicit case requirements.

    Unknown project facts and undocumented case fields receive an ``unknown``
    dimension. They contribute a neutral midpoint so one missing answer does
    not silently become either a pass or a failure.
    """

    fact_map = _fact_map(facts)

    def project(keys: Sequence[str]) -> str:
        return _project_text(fact_map, keys)

    dimensions = [
        _dimension(
            "流程相似度",
            project(
                ("current_workflow_problem", "current_workflow", "desired_outcome")
            ),
            " ".join(
                filter(None, (case.business_problem, case.workflow_scope, case.title))
            ),
            unknown_reason="流程資料或案例工作流範圍未記錄",
            similar_reason="需求流程與案例工作流有相似訊號",
            different_reason="需求流程與案例工作流缺少可比訊號",
        ),
        _dimension(
            "使用者與責任邊界",
            project(("users_and_owners", "human_final_decision")),
            " ".join(
                filter(
                    None,
                    (
                        case.organization_type,
                        *case.applicable_context,
                        *case.human_oversight,
                    ),
                )
            ),
            unknown_reason="使用者、責任或案例監督邊界未記錄",
            similar_reason="使用者或人工責任邊界相近",
            different_reason="使用者或責任邊界需要重新設計",
        ),
        _dimension(
            "系統環境與依賴",
            project(("known_constraints", "system_dependencies")),
            " ".join(case.system_dependencies) or None,
            unknown_reason="系統依賴尚未確認",
            similar_reason="專案環境與案例依賴有重疊",
            different_reason="案例依賴與專案現況不同",
        ),
        _dimension(
            "輸入資料相似度",
            project(("available_data",)),
            " ".join(case.required_inputs) or None,
            unknown_reason="輸入資料或案例要求未記錄",
            similar_reason="輸入資料型態有重疊",
            different_reason="輸入資料需要額外整理或轉換",
        ),
        _dimension(
            "治理條件",
            project(("known_constraints", "governance_conditions")),
            " ".join(case.governance_conditions) or None,
            unknown_reason="治理條件尚未確認",
            similar_reason="治理要求有可沿用部分",
            different_reason="治理條件需要補強",
        ),
        _dimension(
            "決策權限",
            project(("human_final_decision", "decision_authority")),
            " ".join(filter(None, (case.decision_authority, *case.human_oversight)))
            or None,
            unknown_reason="決策權限或人工覆核邊界未記錄",
            similar_reason="案例與專案都保留人工最終決策",
            different_reason="決策權限不可直接照搬",
        ),
        _dimension(
            "部署限制",
            project(("known_constraints", "data_boundary", "processing_boundary")),
            case.processing_boundary,
            unknown_reason="部署邊界尚未確認",
            similar_reason="資料處理與部署邊界相近",
            different_reason="案例部署邊界與專案限制不同",
        ),
        _dimension(
            "第一階段範圍",
            project(("current_workflow_problem", "desired_outcome")),
            " ".join(filter(None, (case.workflow_scope, case.implementation_stage)))
            or None,
            unknown_reason="第一階段範圍尚未確認",
            similar_reason="第一階段可先限制在相似工作流",
            different_reason="案例範圍需要縮小或重新切分",
        ),
    ]
    score = round(sum(item.score for item in dimensions) / len(dimensions))
    known = [
        item for item in dimensions if item.status is not FitDimensionStatus.UNKNOWN
    ]
    if not known:
        level = FitLevel.UNKNOWN
    elif score >= 75:
        level = FitLevel.HIGH
    elif score >= 50:
        level = FitLevel.MEDIUM
    else:
        level = FitLevel.LOW
    similarities = [
        item.basis[0]
        for item in dimensions
        if item.status is FitDimensionStatus.SIMILAR
    ]
    differences = [
        item.basis[0]
        for item in dimensions
        if item.status is FitDimensionStatus.DIFFERENT
    ]
    confirmations = [
        item.basis[0]
        for item in dimensions
        if item.status is FitDimensionStatus.UNKNOWN
    ]
    return ProjectCaseFit(
        level=level,
        score=score,
        dimensions=dimensions,
        similarities=similarities,
        key_differences=differences,
        needs_confirmation=confirmations,
    )


def _gaps(case: ReviewedCase, fit: ProjectCaseFit) -> CaseGapAnalysis:
    ready = list(fit.similarities)
    missing: list[str] = []
    for item in (
        *case.required_inputs,
        *case.system_dependencies,
        *case.governance_conditions,
    ):
        if item not in " ".join(ready):
            missing.append(f"需要確認或補足：{item}")
    not_transferable = [
        f"案例標示的限制：{_case_tag_label(item)}"
        for item in case.non_applicability_tags
    ]
    not_transferable.extend(fit.key_differences)
    return CaseGapAnalysis(
        ready_conditions=ready,
        missing_conditions=list(dict.fromkeys(missing)),
        not_directly_transferable=list(dict.fromkeys(not_transferable)),
        needs_confirmation=fit.needs_confirmation,
    )


def rank_case_matches(
    cases: Iterable[ReviewedCase],
    facts: Iterable[FactRevision],
    *,
    opportunity_types: Sequence[object],
    solution_key: str,
    gate_results: Sequence[ProgramGateResult],
    limit: int = 3,
    eligible_case_ids: set[str] | None = None,
    support_type_by_case: Mapping[str, str] | None = None,
) -> tuple[MatchedCaseAssessment, ...]:
    """Filter reviewed cases, calculate fit, then combine value and fit."""

    if limit < 1:
        return ()
    facts_tuple = tuple(facts)
    opportunities = {str(item) for item in opportunity_types}
    assessment_facts = build_deterministic_assessment_facts(facts_tuple)
    gate_ids = {item.rule_id for item in gate_results}
    ranked: list[tuple[float, int, int, str, MatchedCaseAssessment]] = []
    eligible = eligible_case_ids
    for case in cases:
        if case.review_status is not ReviewStatus.APPROVED:
            continue
        if eligible is not None:
            if case.case_id not in eligible:
                continue
        elif solution_key not in case.applicable_solution_keys:
            continue
        if not opportunities.intersection(
            item.value for item in case.opportunity_types
        ):
            continue
        if _case_conditions_conflict(case, assessment_facts, gate_ids):
            continue
        reference = calculate_case_reference_value(case)
        fit = calculate_project_case_fit(facts_tuple, case)
        gap_analysis = _gaps(case, fit)
        ranking_reasons = [
            "案例已通過審核且與 confirmed project facts 的類型相符",
            f"案例參考價值為 {reference.level.value}，專案適配程度為 {fit.level.value}",
        ]
        ranking_score = fit.score * 0.7 + reference.score * 0.3
        ranked.append(
            (
                -ranking_score,
                -fit.score,
                -reference.score,
                case.case_id,
                MatchedCaseAssessment(
                    case=case,
                    reference_value=reference,
                    project_fit=fit,
                    gaps=gap_analysis,
                    ranking_reasons=ranking_reasons,
                ),
            )
        )
    ranked.sort(key=lambda item: item[:4])
    ordered = [item[4] for item in ranked]
    if support_type_by_case:
        selected: list[MatchedCaseAssessment] = []
        for support_type in ("primary", "supporting"):
            selected.extend(
                item
                for item in ordered
                if support_type_by_case.get(item.case.case_id) == support_type
                and item not in selected
            )
            if len(selected) >= limit:
                break
        selected.extend(item for item in ordered if item not in selected)
        ordered = selected
    return tuple(ordered[:limit])


def _case_conditions_conflict(
    case: ReviewedCase,
    assessment_facts: AssessmentFacts,
    gate_ids: set[str],
) -> bool:
    """Reject a reviewed case before fit scoring when its scope conflicts.

    Conditions remain human-written catalogue fields.  The small mapping below
    translates only the currently reviewed conditions into deterministic facts
    and gates; unknown conditions are never treated as a positive match.
    """

    conditions = set(case.non_applicable_conditions)
    if {"資料或標籤不足", "尚未建立驗證樣本"}.intersection(conditions) and (
        not assessment_facts.data_readiness.data_available
        or not assessment_facts.data_readiness.validation_sample_available
    ):
        return True
    if "需要未經人工確認的自主對外承諾" in conditions and "HG-03" in gate_ids:
        return True
    if "需要系統自行對外承諾或完成最終決策" in conditions and "HG-03" in gate_ids:
        return True
    if (
        "需要系統自行作出具法律或高影響效力的最終決定" in conditions
        and "HG-03" in gate_ids
    ):
        return True
    return False


def derive_recommendation_category(
    facts: Iterable[FactRevision],
    gate_results: Sequence[ProgramGateResult],
) -> RecommendationCategory:
    """Derive the formal route from facts and gates, not provider option choice."""

    facts_tuple = tuple(facts)
    assessment_facts = build_deterministic_assessment_facts(facts_tuple)
    gate_ids = {item.rule_id for item in gate_results}
    if _is_controlled_permission_request_workflow(_all_fact_map(facts_tuple)):
        return RecommendationCategory.RULES_FIRST
    if "HG-03" in gate_ids:
        return RecommendationCategory.GOVERNED_ASSISTIVE
    if (
        assessment_facts.technical_fit.traditional_solution_preferred
        and not assessment_facts.technical_fit.ai_needed
    ):
        return RecommendationCategory.RULES_FIRST
    if (
        not assessment_facts.data_readiness.data_available
        or not assessment_facts.data_readiness.validation_sample_available
    ):
        return RecommendationCategory.READINESS_FIRST
    return RecommendationCategory.AI_HYBRID


def _practice(case_match: MatchedCaseAssessment) -> TransferablePractice | None:
    case = case_match.case
    source_text = case.solution_pattern or case.implementation_method
    if not source_text or not case.source_references:
        return None
    adjustments = list(case_match.gaps.not_directly_transferable)
    if case.decision_authority == "autonomous_action":
        adjustments.append("不得直接複製案例的自主決策能力。")
    if case.non_applicability_tags:
        adjustments.extend(
            f"不適用於：{_case_tag_label(item)}" for item in case.non_applicability_tags
        )
    return TransferablePractice(
        name=case.solution_pattern or "案例中的工作流輔助做法",
        source_case_ids=[case.case_id],
        source_case_titles=[case.title],
        case_evidence=(
            f"{case.organization} 的來源記錄：{source_text}。"
            + (
                "成果："
                + "；".join(case.measurable_outcomes or case.reported_outcomes)
                + "。"
                if case.measurable_outcomes or case.reported_outcomes
                else "成果未記錄。"
            )
        ),
        transferable_part=source_text,
        required_adjustments=list(dict.fromkeys(adjustments))
        or ["先以本專案的人工決策邊界驗證。"],
        current_stage="第一階段 PoC",
        prerequisites=list(case.required_inputs or case.system_dependencies)
        or ["案例前置條件未記錄，需先確認。"],
        not_applicable_scope=[
            _case_tag_label(item) for item in case.non_applicability_tags
        ]
        or ["案例限制未完整記錄。"],
    )


def _gate_impact(gate: ProgramGateResult) -> HardGateImpact:
    disposition = str(gate.disposition.value)
    if disposition == "blocked":
        limits = ["目前不得進入高自動化或高風險執行範圍。"]
    elif disposition == "assistive_only":
        limits = ["只能提供整理、提示或建議，不能取代人工最終決策。"]
    else:
        limits = ["在控制措施完成前，限制部署範圍與資料處理邊界。"]
    return HardGateImpact(
        rule_id=gate.rule_id,
        disposition=disposition,
        affected_stage=gate.affected_stage,
        limits=limits,
        does_not_limit=list(gate.does_not_limit),
        release_conditions=[
            _gate_condition_label(item)
            for item in (gate.release_conditions or gate.required_controls)
        ],
    )


def build_case_centered_assessment(
    *,
    cases: Iterable[ReviewedCase],
    facts: Iterable[FactRevision],
    opportunity_types: Sequence[object],
    solution_key: str,
    recommendation_title: str,
    gate_results: Sequence[ProgramGateResult],
    option_kind: str,
    eligible_case_ids: set[str] | None = None,
    support_type_by_case: Mapping[str, str] | None = None,
) -> CaseCenteredAssessment:
    facts_tuple = tuple(facts)
    matches = rank_case_matches(
        cases,
        facts_tuple,
        opportunity_types=opportunity_types,
        solution_key=solution_key,
        gate_results=gate_results,
        limit=3,
        eligible_case_ids=eligible_case_ids,
        support_type_by_case=support_type_by_case,
    )
    practices = [item for match in matches if (item := _practice(match)) is not None]
    impacts = [_gate_impact(gate) for gate in gate_results]
    recommendation_category = derive_recommendation_category(facts_tuple, gate_results)
    case_ids = [match.case.case_id for match in matches]
    case_basis = [f"以 {match.case.title} 的來源證據作為主要參考" for match in matches]
    if not matches:
        case_basis = ["目前沒有通過審核且與需求相符的成熟案例。"]
    fact_basis = [
        f"已確認需求依據：{_text(fact.value)}"
        for fact in facts_tuple
        if fact.status is FactStatus.CONFIRMED
        and fact.fact_key.strip().casefold() in _MATCHING_FACT_KEYS
    ]
    gate_ids = [item.rule_id for item in impacts]
    constrained = bool(impacts)
    phases = [
        ImplementationPhase(
            phase_name="目前階段",
            description="先整理已確認需求、案例適配與差距，保持低風險人工流程。",
            actions=["確認流程責任邊界", "核對案例前置條件與未知資料"],
            inputs=["已確認需求", "案例適配與差距分析"],
            outputs=["可供審查的第一階段範圍"],
            users=["業務負責人", "流程使用者", "人工審查者"],
            human_decision_boundary="人工負責最終核准與例外處理。",
            not_doing=["不自動執行高風險動作", "不把未知資料視為已確認"],
            source_case_ids=case_ids,
            remaining_gaps=[
                item for match in matches for item in match.gaps.missing_conditions[:2]
            ],
            gate_impacts=gate_ids,
            acceptance_criteria=["每項做法都有案例來源", "未知條件有明確待確認事項"],
        ),
        ImplementationPhase(
            phase_name="第一階段 PoC",
            description="以案例中可移植的輔助做法驗證有限範圍，保留人工決策。",
            actions=["建立小型驗證資料集", "實作建議／檢查流程", "記錄人工覆核結果"],
            inputs=["脫敏或核准資料", "流程規則與案例前置條件"],
            outputs=["可追蹤的輔助結果與覆核紀錄"],
            users=["代表性使用者", "流程 owner", "人工決策者"],
            human_decision_boundary="AI 只整理或提出建議；人工保留最終決策。",
            not_doing=["不自主核准", "不直接寫入真實企業系統"],
            source_case_ids=case_ids,
            remaining_gaps=[
                item for match in matches for item in match.gaps.needs_confirmation[:2]
            ],
            gate_impacts=gate_ids,
            acceptance_criteria=[
                "在既定人工邊界內達成預先定義的流程指標",
                "所有例外可回到人工處理",
            ],
        ),
        ImplementationPhase(
            phase_name="第二階段與後續擴展",
            description="只有在差距與 gate 條件完成後，才評估擴大範圍或自動化程度。",
            actions=[
                "完成治理與安全審查",
                "驗證系統依賴與資料品質",
                "重新評估自動化邊界",
            ],
            inputs=["PoC 驗收紀錄", "已解除的 gate 條件"],
            outputs=["下一階段 go／no-go 判定"],
            users=["業務 owner", "治理與安全 reviewer", "技術 owner"],
            human_decision_boundary="任何高影響決策仍需合格人工最終決定。",
            not_doing=["在條件未解除前不擴大部署"],
            source_case_ids=case_ids,
            remaining_gaps=[
                item
                for match in matches
                for item in match.gaps.not_directly_transferable[:2]
            ],
            gate_impacts=gate_ids,
            acceptance_criteria=["每個擴展動作都有明確前置條件與人工責任"],
        ),
    ]
    if constrained:
        phases[1] = phases[1].model_copy(
            update={
                "description": (
                    "目前 hard gate 限制能力與部署範圍；先做可控的人工輔助 PoC。"
                ),
                "acceptance_criteria": [
                    "所有 gate required controls 已列入驗收",
                    "在限制範圍內完成代表性流程驗證",
                ],
            }
        )
    return CaseCenteredAssessment(
        matching_status="matched" if matches else "no_suitable_reviewed_case",
        matched_cases=list(matches),
        no_case_reason=None
        if matches
        else (
            "沒有足夠的已審核成熟案例可支持正式案例建議；"
            "仍可依 deterministic readiness 與差距規劃下一步。"
        ),
        transferable_practices=practices,
        gate_impacts=impacts,
        phased_path=phases,
        solution_key=solution_key,
        recommendation_title=recommendation_title,
        recommendation_category=recommendation_category,
        recommendation_basis=case_basis
        + fact_basis
        + (["hard gate 只限制目前階段與自動化能力。"] if constrained else [])
        + (
            [f"採用 {recommendation_title} 實施路徑的保守範圍。"] if not matches else []
        ),
    )
