# AI Adoption Case Review — M2.3-lite

## 1. Research scope

本文件審核兩份 Git ignored 的 raw research：`artifacts/deep-research-report (1).md`（以下稱 R1）與 `artifacts/deep-research-report (2).md`（以下稱 R2）。它們是未審核素材，不是專案規格、案例資料庫或可直接引用的事實來源。

本文件只支援 AI PoC Planner 在規劃階段的下列工作：辨識業務需求類型、提出 AI 或非 AI 候選方向、產生澄清問題、提出 PoC KPI 候選、提示人工參與及暫緩／停止訊號，以及提供使用者自行搜尋的案例名稱與關鍵字。

案例資料不得直接決定六維正式分數、權重、hard gates、最終 recommendation、實際技術架構、供應商選型、預算或時程承諾。專案既有的 deterministic scoring 與 hard-gate 契約也不因本文件而改變。

**審核結論摘要：** R1 有 27 個表格案例項目；R2 有 24 個具名案例提及，合計 51 個 raw case entries（未去重）。兩份資料均沒有每個案例可用的原始 URL；R2 的 `turn…` 樣式引用也不是可供本專案追溯的 URL。因此，本輪沒有任何案例符合「具名且可追溯」的 verified case 標準。

## 2. Source and evidence methodology

### 2.1 使用的證據類型

| Evidence type | 定義 | 本輪處理 |
|---|---|---|
| Regulator finding | 監管機關、法院、政府調查或正式執法資料 | 需原始公告 URL；僅寫「FTC」不足以驗證。 |
| Independent research | 有方法、樣本、期間或對照設計的獨立研究 | 需論文／研究 URL 與方法資訊。 |
| Company-reported | 組織自己的法定揭露、公告或具名研究 | 需組織原始頁面 URL；成果仍標示為公司宣稱。 |
| Vendor-reported | 雲端、模型、顧問或產品商發布的客戶案例 | 可證明方案曾存在；成果只能標示為 vendor-reported。 |
| Media-reported | 可信媒體的二手報導 | 需文章 URL，且不得把二手報導升格為原始量測。 |
| Unsourced inference | 報告作者推論、沒有來源、無法確認或泛泛敘述 | 不進入 verified case table。 |

### 2.2 證據等級

| Grade | 準則 |
|---|---|
| A | 可追溯的監管／法院／法定揭露，或方法、樣本、期間明確的獨立研究。 |
| B | 可追溯的企業官方具名資料，且範圍、期間、指標明確。 |
| C | 可追溯的供應商具名客戶案例；成果以 vendor-reported 呈現。 |
| D | 可追溯的可信媒體二手報導。 |
| E | 匿名、沒有原始 URL、引用失效、公司／數字／方案無法配對，或報告自行推論。不得進入 verified case table。 |

本輪未知欄位一律寫為 `unknown`，不以常識、搜尋結果或案例名稱補值。本輪也不聯網補充研究。

### 2.3 事實、宣稱與專案設計的邊界

- **source fact**：能回到原始 URL 並由來源直接支持的陳述。
- **company claim**：公司自己宣稱的成果；即使可追溯，也不等同獨立驗證。
- **vendor claim**：供應商對客戶成果的陳述；不等同獨立驗證。
- **cross-case observation**：跨多個已驗證案例得到的有限觀察；本輪不具備足夠已驗證案例形成此類結論。
- **project design decision**：基於產品安全邊界而採取的設計選擇，必須由 SPEC／scoring／hard-gate 的變更流程處理。

> 單一企業案例不能直接形成永久商業規則。

## 3. Raw research quality review

### R1：`deep-research-report (1).md`

R1 有 27 個表格案例項目，包含成功、供應商宣傳、輔助與失敗／監管四類。主要問題如下：

- 案例表只寫「OpenAI 官方案例」「AWS 官方案例」「FTC 官方聲明」等名稱，沒有原始 URL、發布日期、作者或文件識別碼；所有案例均不可依本輪規則追溯。
- 來源清單與表格不一致。例如表格將 GitHub Copilot 案例寫為安永（EY），來源清單卻列為「Accenture + Copilot」；這使組織、數字與來源的配對無法驗證。
- 多個量化數字沒有期間、樣本、定義或可比基準。例如「98% 日常使用率」「67% 由機器人完成」「100% 缺陷檢出率」；不能判定是否是同一指標的前後比較。
- 多數「停止條件」是作者自行補上的閾值，例如 95%、2%、10%、90%；未顯示為來源事實，不能成為 Planner rule。
- 有匿名案例（未透露的客服、會議紀要）與泛稱案例（法律團隊、醫生團隊、HR 招聘部），不符合具名組織要求。
- Affinda 在成功表與供應商宣傳表重複；此外，行首「——（注意：以下案例由供应商提供）」不是案例但混入案例表。
- 部分技術分類與描述過度概括，例如將 OCR／文件抽取一律寫為生成式 AI，或以「无须持续人工干预」描述視覺檢查，卻沒有部署範圍、例外處理或安全證據。
- 報告把供應商案例、媒體報導與監管資料都標示「高／中」，但沒有依原始證據類型區分，容易把行銷成果誤讀成獨立研究。
- 最後聲稱「30 多個真實案例」及「可直接作為訓練資料」，與其缺少 URL、授權與驗證紀錄的狀況不相容。

### R2：`deep-research-report (2).md`

R2 是較完整的產品與機會類型敘述，不是可審計的案例資料集；其中有 24 個具名案例提及。主要問題如下：

- 全文引用為 `citeturn…` 內部標記，不含來源名稱、原始 URL、日期或可重現的引用書目。這些標記在本 repository 中不可解析。
- 大量框架觀點（Google、Microsoft、NIST、AWS、McKinsey、IBM 等）未附可查 URL，不能確認版本、上下文或原始措辭。
- 案例只列名稱與成果片段；通常沒有基準值、樣本、期間、部署範圍、資料量、人工覆核方式或限制。例如需求預測、客服、開發效率與行銷的數字都無法重算或比較。
- 「可信案例」標籤並非證據等級；它混合公司／供應商宣稱、框架頁面與可能的媒體材料。
- 文件提出 25／20／15／15／15／10 的權重與五項 hard gate，雖標示為建議，仍超出 raw research 可支持的範圍；本輪不得將其帶入既有 deterministic 規則。
- 個別名稱可能是組織、供應商、產品或案例主題，沒有一致的 organization／solution／source 對應，故不能形成案例列。
- 文件有價值的部分是規劃問題、候選 KPI 與安全提醒；它們應視為待產品／人工審核的設計素材，而非外部驗證的研究結論。

## 4. Verified case table

符合條件者必須同時具名、含原始 URL，且能將組織、方案與數字配對。本輪沒有符合條件的案例，因此表格沒有列入任何案例。

| case_id | organization | industry | country_or_region | opportunity_type | business_problem | why_ai_was_considered | solution_direction | poc_or_deployment_scope | baseline_metrics | reported_outcomes | human_oversight | risks_or_limitations | deployment_status | evidence_type | evidence_grade | source_name | source_url | source_date | planner_lessons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| _No eligible cases_ | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

所有 raw research 中提及的案例均保留在下節的弱證據登錄中；它們不是可供檢索或計分的案例資料。

## 5. Failure, stopped, limited and regulatory cases

R1 提及五個失敗、停止、受監管或效果有限案例。它們都缺少本輪要求的原始 URL，所以以下僅記錄 **raw report 的主張**，不當作已證實事實。

| Raw case | 類別 | R1 所稱發生情況 | 原始假設／失敗點 | 人工覆核 | 對 Planner 的警示 | hard-gate 候選 |
|---|---|---|---|---|---|---|
| DoNotPay「機器人律師」 | regulator claim | R1 稱 FTC 限制其律師能力宣稱。 | 將法律協助表述為可替代人類律師；原始執法資料 `unknown`。 | `unknown` | 法律建議不可因宣傳語就視為可自主提供。 | 高影響法律決策缺少合格人工最終決策。 |
| 面部辨識產品 | regulator claim | R1 稱 FTC 認定準確性與偏差宣稱缺乏證據。組織名稱在表格為泛稱；來源清單另提 IntelliVision，配對 `unknown`。 | 精確度／公平性宣稱未能對應可查資料。 | `unknown` | 不可把供應商效能詞彙視為公平性或可靠性證明。 | 高風險辨識用途沒有獨立效能／偏差證據。 |
| Zillow iBuyer | stopped claim | R1 稱 2021 年損失後停止業務。 | 市場變化與模型假設可能失配；金額、期間與因果關係 `unknown`。 | R1 描述為自動購房決策；可核實監督設計 `unknown`。 | 預測應有基準、漂移監測、損失上限與人類決策點。 | 高金額自動決策沒有最壞情境控制。 |
| IBM Watson for Oncology | limited / media claim | R1 稱曾提出不安全治療建議。 | 臨床適用性、資料與治理細節 `unknown`。 | R1 稱醫生審核；範圍與效果 `unknown`。 | 醫療 AI 僅能輔助，需臨床責任人與升級／停止程序。 | 高影響醫療建議沒有人工最終決策或臨床驗證。 |
| Amazon 招聘模型 | stopped / media claim | R1 稱模型偏向男性後停止使用。 | 歷史資料可能反映偏差；來源、樣本與停止決策 `unknown`。 | R1 稱人工最終選取；實際流程 `unknown`。 | 招聘用途須檢查差別影響、申訴與人工覆核，不能把排序當結論。 | 以模型結果直接篩除／錄用，或缺少公平性與申訴機制。 |

上述案例可作為 **hard-gate 候選的人工討論提示**，但不能在本輪新增或調整任何 hard-gate 規則。

## 6. Rejected or weak evidence

| 類別 | 來源位置／案例 | 排除原因 | 可否作一般背景 |
|---|---|---|---|
| no source URL | R1 全部 27 項；R2 全部 24 項提及 | 沒有每案可回溯的原始 URL。 | 僅可作搜尋關鍵字。 |
| broken citation | R2 全文 `turn…` citations | 內部標記不包含可用書目或 URL。 | 否，須先取得原始來源。 |
| anonymous | R1 供應商宣傳表中的未透露客服、未披露會議紀要 | 組織不具名。 | 僅可作非常一般的場景提示。 |
| unclear organization | R1 法律／金融／醫療／HR／醫院／營運團隊等泛稱項目 | 不是可識別組織。 | 否。 |
| duplicate | R1 Affinda | 成功表與供應商宣傳表重複。 | 只保留一個待查名稱。 |
| unclear metric ownership | R1 Morgan Stanley、Klarna、EY／Copilot、WeChat Pay 等量化成果 | 不清楚數字屬公司、供應商、媒體或報告作者。 | 可作 KPI 類型靈感，不能引用數字。 |
| no baseline | R1／R2 多數案例 | 沒有同一指標的導入前基準，無法判斷改善幅度。 | 可作問題類型提示。 |
| no measurement period | R1／R2 多數案例 | 沒有開始、結束或觀察期間。 | 可作背景，不能比較。 |
| vendor marketing only | R1 OpenAI、AWS、Google Cloud、Tencent Cloud 類案例 | 就算來源名稱可信，也未提供 URL 且未有獨立驗證。 | 可作供應商案例搜尋起點。 |
| unsourced threshold | R1 95%、2%、10%、80%／90% 等停止門檻 | 沒有來源或在案內的量測定義。 | 否，不得轉為規則。 |
| report-generated inference | R1「確定性規則清單」；R2 權重與 five gates 建議 | 屬作者歸納或專案設計提案，非案例事實。 | 可供人工討論。 |
| unrelated to Planner scope | R1 Mermaid 的開發、部署、模型訓練流程 | Planner 不負責實作或部署。 | 否。 |

## 7. Candidate AI opportunity types

以下是規劃用 catalog 草案，不是 JSON、Pydantic model 或 deterministic matcher。`related_verified_cases` 目前均為 `unknown`，因本輪沒有已驗證案例。

| opportunity_id / name | business_problem_signals；suitable / unsuitable | minimum_information_needed；clarification_questions | candidate_solution_directions；recommended_human_involvement | candidate_poc_kpis；pause_or_stop_signals | related_verified_cases；search_keywords |
|---|---|---|---|---|---|
| knowledge_query / 企業知識查詢 | 知識散落、重複查問；適合有 owner 的文件；不適合要求代替高風險判斷。 | 核心文件、權限、更新責任；「答案要附來源嗎？誰維護？」 | generative_ai 或 hybrid；中，高風險回答人工確認。 | 帶來源回答率、找答案時間、採用率；權限不清或文件無 owner 時暫緩。 | `unknown`；enterprise knowledge search, grounded Q&A. |
| customer_support_assist / 客服輔助 | 大量重複詢問、需升級複雜案件；不適合自動做補償或法律承諾。 | FAQ、政策、升級規則、現況 CSAT／處理時間；「何時轉人工？」 | generative_ai 或 hybrid；中至高。 | 首問解決、處理時間、正確升級率、CSAT；政策頻繁變更且無維護時暫緩。 | `unknown`；agent assist, customer service escalation. |
| document_extraction / 文件分類與資料抽取 | 文件分類、欄位擷取、重複登打；不適合樣本不可取得或欄位持續變動。 | 樣本、欄位定義、對照答案、敏感資料界線；「例外誰處理？」 | traditional_ml、generative_ai 或 hybrid；低置信度人工覆核。 | 欄位正確率、人工複核率、處理時間；無合法樣本或無例外流程時暫緩。 | `unknown`；document classification, OCR extraction. |
| contract_risk_assist / 合同風險提示 | 審閱耗時、需找紅旗條款；不適合法律結論或自動核准。 | 條款庫、紅旗定義、簽核 owner；「提示後誰作最後判斷？」 | generative_ai + rule_based_automation；高。 | 召回、誤報、審閱時間、人工採用率；無法定標準或無法務簽核時暫緩。 | `unknown`；contract review, clause risk flagging. |
| meeting_summary / 會議摘要與行動項 | 會議紀錄延遲、行動項遺漏；不適合不能錄音或極敏感會議。 | 錄音／逐字稿、摘要格式、保留政策；「誰確認 owner 與期限？」 | generative_ai；低至中。 | 行動項正確率、採用率、整理時間；轉錄品質不足或無使用授權時暫緩。 | `unknown`；meeting transcription, action items. |
| marketing_content_assist / 行銷內容輔助 | 文案變體與審稿量大；不適合沒有品牌／法遵審核就自動發布。 | 品牌規範、禁語、審核流程、目標指標；「誰批准發布？」 | generative_ai；中至高。 | 草稿到批准時間、退稿率、編輯量、轉化指標；審批責任不清時暫緩。 | `unknown`；marketing copy, content approval. |
| software_development_assist / 軟體開發輔助 | 樣板碼、測試、說明與 review 壓力；不適合自動合併高風險程式。 | 倉庫範圍、測試／review 基線、安全限制；「哪些變更絕不自動提交？」 | generative_ai；高。 | 建議採用率、review 時間、缺陷外溢、開發者滿意度；無 review／測試基線時暫緩。 | `unknown`；coding assistant, pull request review. |
| sales_lead_analysis / 銷售線索分析 | CRM 整理與優先排序困難；不適合 CRM 資料斷裂或把模型當唯一裁決。 | 漏斗定義、歷史互動／結果、資料品質；「什麼叫合格線索？」 | data_analytics、traditional_ml、generative_ai 或 hybrid；中。 | 準備時間、排序品質、轉化率、採用率；無共同欄位與結果定義時暫緩。 | `unknown`；lead scoring, sales copilot. |
| demand_forecasting / 需求預測 | 補貨、排班、產能預測失準；不適合資料短缺或口徑不一致。 | 時序資料、決策週期、外生變數、目前誤差；「誤差造成什麼成本？」 | traditional_ml、data_analytics；例外人工確認。 | MAPE／WAPE、缺貨、庫存周轉、浪費；沒有現況誤差基準時暫緩。 | `unknown`；demand forecasting, time series. |
| anomaly_fraud_detection / 異常與詐欺偵測 | 低頻高損失異常、需調查；不適合沒有標註或人工調查容量。 | 異常定義、案例／標籤、誤報／漏報成本、回饋；「誰調查與覆核？」 | rule_based_automation + traditional_ml，必要時 generative_ai 輔助摘要；高。 | precision、recall、FPR、調查週期；直接依模型處罰或無覆核時 block。 | `unknown`；fraud detection, anomaly investigation. |
| visual_quality_inspection / 視覺品質檢查 | 重複外觀檢查、固定拍攝位；不適合光線／相機不穩或缺陷定義主觀。 | 圖片、標註、相機條件、漏檢成本；「低置信度去哪裡？」 | traditional_ml；中。 | 漏檢、誤檢、檢驗速度、人工複判率；缺陷樣本不足或無法接受漏檢成本時暫緩。 | `unknown`；visual inspection, defect detection. |
| hiring_operations_assist / 招聘流程輔助 | JD、履歷摘要、排程耗時；不適合自動淘汰或錄用。 | 職能模型、流程、合規 owner、人工覆核與申訴；「系統會否影響錄用？」 | generative_ai、data_analytics；高，assistive-only。 | 招募作業時間、人工一致性、候選人體驗；無人工覆核／申訴或直接篩除時 block。 | `unknown`；recruiting assist, resume summary. |
| workflow_automation / 一般流程自動化 | 規則固定、輸入輸出穩定、重複搬資料；不適合需要語意推論或預測。 | SOP、例外清單、系統界線、錯誤成本；「規則可否完整列舉？」 | rule_based_automation 或 conventional_software；例外人工處理。 | 自動完成率、例外率、處理時間、錯誤率；例外無 owner 或規則不穩定時暫緩。 | `unknown`；workflow automation, RPA. |
| decision_dashboard / 資料分析與決策儀表板 | 需要看趨勢、分群、原因與共同口徑；不適合資料定義未對齊。 | 資料來源、指標定義、更新頻率、使用者；「要支援哪個決策？」 | data_analytics 或 conventional_software；決策者保留判斷。 | 資料新鮮度、報表使用率、決策週期；資料口徑衝突或無 owner 時暫緩。 | `unknown`；business intelligence, decision dashboard. |

## 8. Technology direction decision guidance

本節是 **project design decision** 的候選指引，不是本輪從 raw cases 驗證出的固定規則。

| 方向 | 規劃層級判斷 | 標示 |
|---|---|---|
| Rule-based automation | 規則清楚、輸入輸出固定、例外少，且決策不需語意理解或預測時優先考慮。 | project design decision |
| Conventional software | 問題主要是表單、權限、資料庫、通知、流程或系統整合，而非推論／生成時優先考慮。 | project design decision |
| Data analytics | 目標是了解趨勢、分群、異常或原因，且不需要模型自動預測或採取動作時優先考慮。 | project design decision |
| Traditional ML | 有足夠、合法且相對穩定的歷史資料與量化目標，任務是分類、預測、排序或異常偵測時列為候選。 | project design decision |
| Generative AI | 任務核心是文字、文件、對話或內容生成，且可設計來源依據、人工覆核、接受率與重大錯誤觀察時列為候選。 | project design decision |
| AI Agent | 只有任務確實需要多步驟、依中間結果選下一步、多工具／系統、狀態保存、明確權限與人工批准點時才列為候選。 | project design decision |
| Do not use AI | 沒有明確業務目標、沒有可用資料、不能定義成功、錯誤成本不可接受、一般軟體已足夠，或只因潮流而導入時，建議不使用或暫緩。 | project design decision |

這些判斷不可被包裝為「source fact」或以 R1／R2 的數字設定固定門檻。

## 9. Cross-case planning lessons

因沒有已驗證案例，下列是與既有專案安全邊界一致的 **project design decision**，不是 cross-case evidence。

- 資料來源、資料 owner、合法使用範圍或更新責任不明時，先補資料與治理資訊。
- 需要聲稱改善時，先建立同一指標、同一範圍與同一期間的 baseline。
- 法律、醫療、招聘、信用、財務等高影響結果只可 assistive；保留具實質意義的人類最終決策。
- 影響個人權益或可被拒絕／懲罰的流程，應設人工覆核、例外處理與適當的申訴／更正路徑。
- 異常、詐欺、品質檢查等任務不能只看 accuracy；應按情境觀察誤報、漏報及其成本。
- 高損失或不可逆後果的流程，應評估最壞情境、回退方式與人工中斷點。
- 沒有資料基準、使用者不採用、例外量過大、風險控制無法關閉，均是不擴大 PoC 的訊號。
- 沒有明確目標、owner、合法權限、可比較 baseline 或人工決策邊界時，應暫緩或由既有 hard-gate engine 判定 block／assistive-only。

不建立 95%、2% 或其他固定閾值；具體門檻應由每個 PoC 的業務 owner、風險與 baseline 共同決定。

## 10. Recommended evaluation cases

下表是匿名化評估素材，不是測試程式碼，也不是正式 catalog。每案的 `related_verified_cases` 均為 `unknown`。

| evaluation_id | user_request | expected_direction | acceptable_alternative_directions | expected_opportunity_types | missing_information | required_human_involvement | candidate_poc_kpis | pause_or_block_signals | must_not_recommend | related_verified_cases |
|---|---|---|---|---|---|---|---|---|---|---|
| EV-01 | 將固定格式的請款資料搬到既有系統。 | rule_based_automation | conventional_software | workflow_automation | SOP、例外率 | 例外人工處理 | 自動完成率、例外率、時間 | 規則不可列舉 | generative_ai、ai_agent | `unknown` |
| EV-02 | 建立有權限、通知與簽核的採購流程。 | conventional_software | rule_based_automation | workflow_automation | 角色、流程、整合系統 | 簽核人 | 完成時間、退件率 | 權限／流程未定 | generative_ai、ai_agent | `unknown` |
| EV-03 | 主管要整合營運數字並看異常。 | data_analytics | conventional_software | decision_dashboard | KPI 定義、資料口徑 | 主管判讀 | 資料新鮮度、使用率 | 口徑不一致 | ai_agent | `unknown` |
| EV-04 | 依歷史銷售規劃下月庫存。 | traditional_ml | data_analytics | demand_forecasting | 歷史長度、誤差基準、外因 | 規劃者確認例外 | WAPE／MAPE、缺貨、庫存 | 無連續資料或 baseline | generative_ai 作主要預測器 | `unknown` |
| EV-05 | 根據產線照片提示可能瑕疵。 | traditional_ml | hybrid | visual_quality_inspection | 圖片、標註、漏檢成本 | 低置信度覆判 | 漏檢、誤檢、速度 | 相機不穩或無樣本 | generative_ai 作首選 | `unknown` |
| EV-06 | 回答員工制度與 SOP 問題並附來源。 | generative_ai | hybrid | knowledge_query | 文件、權限、owner | 高風險答案確認 | 帶來源率、找答案時間、採用率 | 權限或更新機制不清 | 自動執行人事／財務動作 | `unknown` |
| EV-07 | 協助客服摘要案件與建議回覆。 | generative_ai | hybrid | customer_support_assist | 政策、升級規則、CSAT baseline | 客服核可；補償／投訴升級 | AHT、CSAT、升級正確率 | 無轉人工邊界 | 無監督自動承諾 | `unknown` |
| EV-08 | 抽取發票欄位並送入人工複核佇列。 | hybrid | traditional_ml | document_extraction | 樣本、欄位定義、PII 規則 | 低置信度與例外覆核 | 欄位正確率、複核率、時間 | 資料不可合法使用 | 無校驗直接入帳 | `unknown` |
| EV-09 | 幫法務標記合約紅旗條款。 | generative_ai | hybrid | contract_risk_assist | 條款庫、紅旗定義、簽核權責 | 律師最終決策 | 召回、誤報、審閱時間 | 無法務 owner | 自動法律結論／核准 | `unknown` |
| EV-10 | 讓 AI 直接淘汰履歷並決定錄用。 | blocked | assistive-only | hiring_operations_assist | 合規、偏差檢查、申訴、人工流程 | 人工最終決策必須存在 | 作業時間、人工一致性 | 自動篩除或無申訴 | 自主錄用／淘汰 | `unknown` |
| EV-11 | 用交易資料找可疑案件，直接凍結帳戶。 | assistive-only | traditional_ml + rules | anomaly_fraud_detection | 標註、損失、覆核量能 | 調查人員最終處置 | precision、recall、FPR | 直接處罰或無覆核 | 自主制裁 | `unknown` |
| EV-12 | 做跨採購、人資、財務系統的「萬能 Agent」。 | more_information / staged | 拆分後的 generative_ai 或 conventional_software | `unknown` | 目標、權限、動作清單、批准點 | 每個高風險動作批准 | 任務完成、人工 override、錯誤成本 | 範圍過大、權限不清 | 直接推薦 ai_agent 上線 | `unknown` |
| EV-13 | 老闆要求「我們也要 AI」，但沒有問題、資料或 owner。 | do_not_use_ai / pause | conventional_software | `unknown` | 業務目標、owner、成功定義 | 人工先定義需求 | `unknown` | 核心資訊缺失 | 任何 AI 方案 | `unknown` |
| EV-14 | 會議後自動整理摘要與待辦。 | generative_ai | conventional_software | meeting_summary | 錄音授權、格式、敏感性 | owner 確認待辦 | 採用率、待辦正確率、時間 | 無授權或轉錄不可靠 | 自動外傳敏感內容 | `unknown` |
| EV-15 | 讓開發者產生測試與文件，但保留 PR review。 | generative_ai | hybrid | software_development_assist | repo 範圍、測試、資安規則 | 工程師 review／merge | 建議採用率、review 時間、缺陷 | 無測試與 review | 自動合併正式程式 | `unknown` |

## 11. Recommendation for M2.3-lite

1. **可進入正式 catalog 的 opportunity types：** 本輪沒有足夠已驗證案例可作為「案例支持」；但知識查詢、客服輔助、文件抽取、需求預測、視覺檢查、合同提示、會議摘要、開發輔助、一般流程自動化與資料分析，仍可由產品團隊以既有 SPEC 與人工審核決定是否收錄為非案例依賴的 catalog 草案。
2. **證據較弱的候選：** 銷售線索分析、行銷內容、AI Agent、招聘與詐欺案例在 raw research 中缺少可追溯材料；僅能作候選與追問模板。
3. **適合 deterministic matching 的欄位：** 業務問題信號、資料是否存在、輸入／輸出是否固定、是否需要預測、是否是非結構化文字／文件、是否需要多步工具、權限是否清楚、部署動作是否可逆、已知高影響領域、baseline 是否存在。
4. **適合 LangChain／LLM 的欄位：** 模糊需求理解、業務目標歸納、結構化意圖抽取、澄清問題生成、候選方向說明、報告敘述整理；不得由 LLM 決定正式分數、gate 或唯一 recommendation。
5. **必須由 deterministic scoring engine 決定的內容：** 六維評分、權重套用、分數理由的結構、缺失資訊處理與 recommendation 排序。
6. **必須由 hard-gate engine 決定的內容：** 高風險決策邊界、assistive-only、人工最終決策要求、暫緩或 block。這是既有專案契約，非本研究新增規則。
7. **只能作參考、不得成為規則的內容：** R1／R2 所有案例數字、百分比、節省金額、準確率、停止門檻與權重提議。
8. **是否建議進入 M2.3-lite implementation：** **尚不建議僅依本研究進入。** 先由人工確認 catalog 的產品範圍，並補一組具原始 URL、來源日期、證據類型與授權／可公開性審核的案例資料；再依既有規格決定是否啟動實作。
9. **實作前仍需人工確認：** catalog 是否可在「零 verified cases」下以合成／規格導向資料起步、每個機會類型的可公開來源、案例引用與授權政策、評估案例是否要正式化為測試資料，以及既有 scoring／hard-gate 與 catalog 欄位的契約對應。

### 責任邊界

| 元件 | 責任 |
|---|---|
| LangChain／LLM | 理解模糊需求、歸納目標、抽取結構化意圖、生成追問、解釋候選方案、整理報告。 |
| Catalog matching | 將結構化意圖對應 1–3 個候選 opportunity types，提供候選方向、追問、KPI 與參考案例；不決定最終 recommendation。 |
| Deterministic scoring engine | 六維評分、權重、分數說明、缺失資訊與 recommendation 排序。 |
| Hard-gate engine | 高風險決策邊界、assistive-only、人工最終決策、暫緩或 block。 |

## Audit counts

| 項目 | 數量 |
|---|---:|
| R1 raw 表格案例項目 | 27 |
| R2 raw 具名案例提及 | 24 |
| Raw case entries 合計（未去重） | 51 |
| 具名且可追溯的 verified cases | 0 |
| Grade A / B / C / D | 0 / 0 / 0 / 0 |
| Grade E | 51 |
| R1 失敗、停止、受監管或效果有限案例 | 5 |
| 可用於正式 deterministic rule 的 raw case 數字 | 0 |
