"""Versioned, human-reviewed content for the SQLite runtime catalogue.

This module is deliberately the review surface for formal solution and case
content.  It is only used by the schema migration; requests read the resulting
SQLite rows through ``SQLiteSolutionCatalogRepository``.
"""

# ruff: noqa: E501

from __future__ import annotations

from ai_poc_planner.domain.catalog import EvidenceType, OpportunityType
from ai_poc_planner.domain.reviewed_cases import (
    CaseSourceReference,
    ReviewedCase,
    ReviewedEvidenceGrade,
    ReviewStatus,
)
from ai_poc_planner.domain.solution_catalog import SolutionPattern

_STAMP = "2026-07-28T00:00:00+00:00"
_CONTENT_VERSION = "2026.07.29.1"


def reviewed_solution_patterns() -> tuple[SolutionPattern, ...]:
    """Return immutable editorial records to seed an empty SQLite catalogue."""

    return (
        SolutionPattern(
            solution_key="knowledge_retrieval_human_review",
            recommendation_category="ai_hybrid",
            display_name_zh="文件知識檢索與人工審核輔助",
            short_description_zh="從核准文件找出相關內容、標示來源並提供草稿，由人員確認後使用。",
            detailed_description_zh="先把核准的產品文件、FAQ 與標準答案整理為可追溯知識來源，再讓使用者以自然語言查找內容與取得附來源的草稿。系統只協助檢索與整理，不取代人員對內容、例外或對外使用的判斷。",
            suitable_when_zh="問題主要是文件分散、查找耗時，且已有可核准使用的文件、FAQ 或標準答案可供驗證時適用。",
            not_suitable_when_zh="若流程主要是固定欄位與明確條件判斷，或文件來源、版本責任尚未釐清，應先採規則流程或資料準備。",
            typical_scope_zh="先挑選有限主題、核准文件與代表性問題，驗證檢索、來源呈現、草稿與人工修訂流程。",
            human_boundary_zh="人員確認來源、修改草稿並決定是否使用；系統不得自行承諾、發送或執行後續動作。",
            expected_outputs_zh="可追溯的知識清單、附來源的候選內容、人工修訂紀錄與代表性問題的驗證結果。",
            acceptance_focus_zh="檢查來源是否正確、查找時間是否改善、人工修訂是否可回溯，以及例外是否都回到人員處理。",
            review_status=ReviewStatus.APPROVED,
            content_version=_CONTENT_VERSION,
            created_at=_STAMP,
            updated_at=_STAMP,
        ),
        SolutionPattern(
            solution_key="rules_and_human_approval",
            recommendation_category="rules_first",
            display_name_zh="流程標準化、規則檢查與人工核准",
            short_description_zh="把固定欄位、規則與例外整理成可檢查流程，仍由人員處理例外與最終核准。",
            detailed_description_zh="先定義表單欄位、條件規則與例外處理方式，再由系統提示漏項、超限或不符合條件的內容。規則結果只提供一致的檢查依據，最終審核與責任判斷仍留在人員手中。",
            suitable_when_zh="輸入格式穩定、規則可明確列出，且主要痛點是漏填、漏檢或人工重複檢查時適用。",
            not_suitable_when_zh="若必須處理大量未結構化判斷、規則尚未成形，或例外無法由責任人定義時，不應直接把流程自動化。",
            typical_scope_zh="先整理表單、規則清單與例外樣本，在既有內部流程中驗證提示與人工覆核。",
            human_boundary_zh="人員維護規則、判斷例外並完成最終核准；系統只檢查已核准的條件。",
            expected_outputs_zh="可維護的規則清單、表單檢查結果、例外處理紀錄與人工審核紀錄。",
            acceptance_focus_zh="檢查漏項與漏檢是否下降、規則命中是否正確，以及例外是否完整回到人工處理。",
            review_status=ReviewStatus.APPROVED,
            content_version=_CONTENT_VERSION,
            created_at=_STAMP,
            updated_at=_STAMP,
        ),
        SolutionPattern(
            solution_key="permission_request_rules_and_human_approval",
            recommendation_category="governed_assistive",
            display_name_zh="權限申請標準化、規則檢查與人工審批",
            short_description_zh="以職位與權限範本整理申請、檢查固定規則，並保留主管審批與 IT 開通責任。",
            detailed_description_zh="將權限申請表、職位—權限範本與固定檢查規則整理成可追溯流程。系統可提示漏項、比對既定規則並彙整申請資料；主管必須作出最終審批，IT 僅依已核准結果執行開通。",
            suitable_when_zh="申請格式、權限範本、固定檢查規則與主管審批責任可以界定，且第一階段不直接寫入高風險系統時適用。",
            not_suitable_when_zh="職位—權限範本、審批規則或資料使用授權尚未釐清時，不應擴大到自動核准或直接開通權限。",
            typical_scope_zh="先驗證申請表、職位—權限範本、規則清單、主管審批與稽核紀錄，不處理自動開通。",
            human_boundary_zh="主管保留最終審批；IT 依已核准結果開通；系統不得自行審批、拒絕或開通權限。",
            expected_outputs_zh="完整申請資料、規則檢查結果、人工審批紀錄、例外處理紀錄與可追溯稽核資料。",
            acceptance_focus_zh="檢查申請格式完整率、規則提示正確率、主管審批處理時間、例外紀錄完整性與稽核紀錄完整性，而非追求自動開通。",
            review_status=ReviewStatus.APPROVED,
            content_version=_CONTENT_VERSION,
            created_at=_STAMP,
            updated_at=_STAMP,
        ),
        SolutionPattern(
            solution_key="data_readiness_validation",
            recommendation_category="readiness_first",
            display_name_zh="資料與驗證基礎建設",
            short_description_zh="先補足資料、標籤與驗證設計，再判斷是否進入模型或系統實作。",
            detailed_description_zh="先盤點可用資料、定義標籤與判定基準，並建立代表性樣本與獨立驗證集。此階段的目標是讓後續選型有可靠依據，不承諾模型準確率或立即擴大到正式環境。",
            suitable_when_zh="資料量、標籤、品質或驗證樣本不足，尚無法可靠評估模型或自動化效果時適用。",
            not_suitable_when_zh="若資料、標籤與驗證設計已成熟，且流程需求明確，應直接評估對應的受控方案而非停留在資料盤點。",
            typical_scope_zh="先完成資料清單、標註規則、代表性樣本、獨立驗證集與錯誤分類方式。",
            human_boundary_zh="領域人員負責定義標籤與判定基準；工程負責人確認資料版本與驗證設計；系統不替代驗收結論。",
            expected_outputs_zh="資料清單、標註規則、代表性樣本、驗證集與後續評估條件。",
            acceptance_focus_zh="檢查樣本代表性、標註一致性、資料版本與驗證設計是否足以支持下一階段。",
            review_status=ReviewStatus.APPROVED,
            content_version=_CONTENT_VERSION,
            created_at=_STAMP,
            updated_at=_STAMP,
        ),
    )


def reviewed_cases() -> tuple[ReviewedCase, ...]:
    """Return source-backed cases whose report facts were manually written."""

    return (
        ReviewedCase(
            case_id="case-01",
            organization="Morgan Stanley",
            title="企業知識檢索與顧問工作輔助",
            original_title="Morgan Stanley uses AI evals to shape the future of financial services",
            display_title_zh="Morgan Stanley：企業知識檢索與人工覆核",
            summary_zh="以內部知識檢索與評估流程協助財務顧問查找資訊，並由顧問檢查輸出。",
            case_summary_zh="Morgan Stanley 將內部知識檢索與評估流程納入顧問工作，讓顧問查找資料與整理資訊時有可檢查的輔助。",
            problem_context_zh="財務顧問需要在大量內部文件中快速取得可靠資訊，並維持專業服務所需的品質與一致性。",
            implemented_approach_zh="建立內部問答與會議摘要工具，使用真實工作情境的評估資料檢查輸出，並由顧問修訂後定稿。",
            documented_outcomes_zh="來源記錄顧問團隊對內部工具的高採用率，以及文件查找效率與可存取文件範圍的改善；這些數字屬案例提供者揭露。",
            transferable_practices_zh="先以代表性問題建立評估集、保留來源查找與人工修訂，再逐步擴大文件範圍。",
            limitations_zh="此案例的金融服務環境、文件規模、法規責任與內部控制不同；本專案不得照搬其部署規模或自動化程度。",
            applicable_solution_keys=["knowledge_retrieval_human_review"],
            applicable_conditions=["有核准的內部知識來源", "人員保留內容確認責任"],
            non_applicable_conditions=["需要系統自行對外承諾或完成最終決策"],
            opportunity_types=[
                OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
            ],
            business_problem="企業內部知識查找與專業人員工作輔助。",
            implementation_method="以內部知識檢索、評估與人工修訂協助工作。",
            reported_outcomes=["來源記錄指出文件查找效率與採用度改善。"],
            applicability_tags=["knowledge_retrieval", "human_review"],
            non_applicability_tags=["autonomous_action"],
            human_oversight=["顧問在定稿前檢查與修訂輸出。"],
            risks_or_limitations=["案例成效主要由案例提供者揭露。"],
            evidence_type=EvidenceType.VENDOR_REPORTED,
            evidence_grade=ReviewedEvidenceGrade.C,
            source_name="OpenAI 客戶案例：Morgan Stanley",
            source_url="https://openai.com/index/morgan-stanley/",
            source_references=[
                CaseSourceReference(
                    label="OpenAI 客戶案例：Morgan Stanley",
                    url="https://openai.com/index/morgan-stanley/",
                )
            ],
            review_status=ReviewStatus.APPROVED,
            review_notes="來源為供應商客戶案例；成效敘述僅採其公開記錄。",
            reviewed_at=_STAMP,
            content_version=_CONTENT_VERSION,
        ),
        ReviewedCase(
            case_id="case-02",
            organization="Klarna",
            title="客服 AI 助理",
            original_title="Klarna's AI assistant does the work of 700 full-time agents",
            display_title_zh="Klarna：客服 AI 助理",
            summary_zh="以 AI 協助處理客服對話，案例成效由來源提供者揭露。",
            case_summary_zh="Klarna 將 AI 助理應用於客服對話與購物服務，案例描述包含多語言服務與對話處理。",
            problem_context_zh="客服團隊需回應大量消費者問題，同時縮短處理時間並維持服務品質。",
            implemented_approach_zh="以 AI 助理處理部分客服對話，並擴大生成式 AI 在內部員工工作中的使用。",
            documented_outcomes_zh="來源記錄上線初期的對話量、處理效率與滿意度比較；這些數字屬案例提供者揭露。",
            transferable_practices_zh="先從常見問題與明確服務範圍開始，持續檢查服務品質與人工介入需要。",
            limitations_zh="案例包含面向消費者的自動化服務與特定產品情境；本專案必須自行決定人工確認與對外發送邊界。",
            applicable_solution_keys=["knowledge_retrieval_human_review"],
            applicable_conditions=[
                "客服或服務流程可限定問題範圍",
                "人工責任與例外處理已明確",
            ],
            non_applicable_conditions=["需要未經人工確認的自主對外承諾"],
            opportunity_types=[OpportunityType.CUSTOMER_SERVICE_ASSIST],
            business_problem="客服對話與服務流程輔助。",
            implementation_method="以 AI 助理處理部分客服對話與服務流程。",
            reported_outcomes=["來源記錄客服對話處理與服務效率的案例成效。"],
            applicability_tags=["customer_service", "bounded_scope"],
            non_applicability_tags=["autonomous_action"],
            human_oversight=["本專案需另行定義人工確認與例外處理。"],
            risks_or_limitations=["案例成效主要由案例提供者揭露。"],
            evidence_type=EvidenceType.VENDOR_REPORTED,
            evidence_grade=ReviewedEvidenceGrade.C,
            source_name="OpenAI 客戶案例：Klarna",
            source_url="https://openai.com/index/klarna/",
            source_references=[
                CaseSourceReference(
                    label="OpenAI 客戶案例：Klarna",
                    url="https://openai.com/index/klarna/",
                )
            ],
            review_status=ReviewStatus.APPROVED,
            review_notes="案例含對外服務自動化，僅可用於界定服務範圍與人工邊界的比較。",
            reviewed_at=_STAMP,
            content_version=_CONTENT_VERSION,
        ),
        ReviewedCase(
            case_id="case-04",
            organization="Ironclad",
            title="合約審查輔助",
            original_title="Simplifying contract reviews with AI",
            display_title_zh="Ironclad：合約審查與人工覆核",
            summary_zh="以 AI 協助辨識合約異常與提出修改建議，使用者可接受、拒絕或停用建議。",
            case_summary_zh="Ironclad 將 AI 輔助納入合約審查，提供異常辨識、條款建議與使用者可控制的修訂流程。",
            problem_context_zh="法務團隊需要在合約工作流程中辨識異常內容並維持既有條款與審查控制。",
            implemented_approach_zh="在合約編輯流程中提供異常標示、預先核准條款與文字建議，使用者可接受、拒絕或關閉 AI 功能。",
            documented_outcomes_zh="來源記錄指出使用者處理初步合約修訂所需時間縮短；此成效由案例提供者揭露。",
            transferable_practices_zh="把候選建議放在既有工作流程中，保留接受、拒絕與關閉功能，並讓人員掌握最終修訂。",
            limitations_zh="合約審查的法律責任、文件類型與系統整合方式不同；本專案不能把建議視為已核准結論。",
            applicable_solution_keys=["knowledge_retrieval_human_review"],
            applicable_conditions=[
                "使用者可檢查、接受或拒絕候選內容",
                "來源與修訂責任可追溯",
            ],
            non_applicable_conditions=["需要系統自行作出具法律或高影響效力的最終決定"],
            opportunity_types=[
                OpportunityType.ENTERPRISE_KNOWLEDGE_AND_PROFESSIONAL_DOCUMENT_ASSIST
            ],
            business_problem="合約內容理解與人工審查輔助。",
            implementation_method="在既有合約工作流程中提供候選建議並保留使用者控制。",
            reported_outcomes=["來源記錄使用者處理初步修訂所需時間縮短。"],
            applicability_tags=["human_review", "document_assist"],
            non_applicability_tags=["autonomous_action"],
            human_oversight=["使用者可接受、拒絕或停用候選建議。"],
            risks_or_limitations=["案例成效主要由案例提供者揭露。"],
            evidence_type=EvidenceType.VENDOR_REPORTED,
            evidence_grade=ReviewedEvidenceGrade.C,
            source_name="OpenAI 客戶案例：Ironclad",
            source_url="https://openai.com/index/ironclad/",
            source_references=[
                CaseSourceReference(
                    label="OpenAI 客戶案例：Ironclad",
                    url="https://openai.com/index/ironclad/",
                )
            ],
            review_status=ReviewStatus.APPROVED,
            review_notes="來源為供應商客戶案例；案例事實僅採公開記錄。",
            reviewed_at=_STAMP,
            content_version=_CONTENT_VERSION,
        ),
        ReviewedCase(
            case_id="case-07",
            organization="CrossTech",
            title="預測性維護",
            original_title="CrossTech case study",
            display_title_zh="CrossTech：預測性維護資料與模型運作",
            summary_zh="以影像資料、AI 模型與維運流程支援交通基礎設施的預測性維護。",
            case_summary_zh="CrossTech 使用影像與 AI 模型協助基礎設施維護，案例前提是已有可支援模型開發與部署的資料與系統能力。",
            problem_context_zh="交通網路維護需從人工巡檢轉向更即時的風險辨識與維護安排。",
            implemented_approach_zh="使用列車影像與電腦視覺辨識潛在風險，並透過雲端基礎設施支援模型開發與部署。",
            documented_outcomes_zh="來源記錄模型開發與部署時間改善，以及關鍵路線高風險故障降低；這些數字屬案例提供者揭露。",
            transferable_practices_zh="先確認影像資料、標註、驗證與維運流程，再評估模型與部署方式。",
            limitations_zh="案例已有特定影像資料、模型與雲端運作能力；資料不足或沒有穩定標籤時，不能把它當成可直接複製的 PoC 證據。",
            applicable_solution_keys=["data_readiness_validation"],
            applicable_conditions=["已有代表性資料、穩定標籤與可驗證的維護情境"],
            non_applicable_conditions=["資料或標籤不足", "尚未建立驗證樣本"],
            opportunity_types=[OpportunityType.PREDICTIVE_MAINTENANCE],
            business_problem="以影像資料支援基礎設施預測性維護。",
            implementation_method="以電腦視覺模型與維運流程辨識潛在風險。",
            reported_outcomes=["來源記錄模型開發、部署與高風險故障改善。"],
            applicability_tags=["predictive_maintenance", "validated_data"],
            non_applicability_tags=["insufficient_data", "missing_labels"],
            human_oversight=["維運團隊仍需依實際風險判斷維護行動。"],
            risks_or_limitations=[
                "案例成效主要由案例提供者揭露，且資料與部署條件不同。"
            ],
            evidence_type=EvidenceType.VENDOR_REPORTED,
            evidence_grade=ReviewedEvidenceGrade.C,
            source_name="Google Cloud 客戶案例：CrossTech",
            source_url="https://cloud.google.com/customers/crosstech",
            source_references=[
                CaseSourceReference(
                    label="Google Cloud 客戶案例：CrossTech",
                    url="https://cloud.google.com/customers/crosstech",
                )
            ],
            review_status=ReviewStatus.APPROVED,
            review_notes="案例只支援資料與驗證條件已具備時的比較，不能補足本專案缺少的標籤。",
            reviewed_at=_STAMP,
            content_version=_CONTENT_VERSION,
        ),
    )
