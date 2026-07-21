# AI Adoption Case Review — M2.3-lite

## 1. Research scope

本文件審核兩份 Git ignored 的 raw research：`artifacts/deep-research-report (1).md`（以下稱 R1）與 `artifacts/deep-research-report (2).md`（以下稱 R2）。它們是未審核素材，不是專案規格、案例資料庫或可直接引用的事實來源。

本文件只支援 AI PoC Planner 在規劃階段的下列工作：辨識業務需求類型、提出 AI 或非 AI 候選方向、產生澄清問題、提出 PoC KPI 候選、提示人工參與及暫緩／停止訊號，以及提供使用者自行搜尋的案例名稱與關鍵字。

案例資料不得直接決定六維正式分數、權重、hard gates、最終 recommendation、實際技術架構、供應商選型、預算或時程承諾。專案既有的 deterministic scoring 與 hard-gate 契約也不因本文件而改變。

**審核結論摘要：** R1 有 27 個表格案例項目；R2 有 24 個具名案例提及，合計 51 個 raw case entries（未去重）。本輪新增審核 `artifacts/AI_ADOPTION_CASE_SOURCE_LINKS.md`（以下稱來源包）：它提供 30 個具名案例的原始 URL、發布機構與證據類型。當中 11 個可直接或經組織名稱正規化對應 R1；另有 1 個 Accenture／GitHub Copilot 來源用來識別 R1 的 EY 名稱錯置，但不使 EY raw entry 合格。R2 沒有可逐案恢復的 URL；其餘 18 個是同一規劃領域的來源包補充案例，不能倒填成 R1／R2 的原始內容。所有未由來源包明確支持的欄位維持 `unknown`。

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
| A | 可追溯的監管／法院／法定揭露，或方法、樣本、期間明確的獨立研究。可作為較強參考。 |
| B | 可追溯的企業正式法定揭露、官方公告或具名資料，且範圍、期間或指標可辨。可作為較強參考，但成果仍是該組織的陳述。 |
| C | 可追溯的供應商具名客戶案例或 vendor-participated research。可作為較強參考，但成果必須標示為 vendor-reported 或 vendor-participated，並非獨立驗證。 |
| D | 可追溯的可信二手媒體、客戶／合作夥伴或其他非獨立案例來源。可以顯示為真實企業案例，但必須清楚標示其非獨立來源性質。 |
| E | 匿名、沒有原始 URL、引用失效、公司／數字／方案無法配對，或報告自行推論。僅能作補充參考，不得支撐正式規則、分數、hard gate 或主要推薦。 |

本輪未知欄位一律寫為 `unknown`，不以常識、搜尋結果或案例名稱補值。本輪也不聯網補充研究。來源包可支持案例身分、原始 URL、發布者、證據類型，以及其明確列出的少數頁面主張；它**不能**自動支持 raw research 的其他數字、基準、期間、樣本、人工參與或停止門檻。

### 2.3 Evidence policy（人工核准）

- Grade A、B、C 可作為較強參考；它們的來源類型仍必須保留在案例說明中。
- Grade D 可以顯示為真實企業案例，但必須清楚標示為供應商、客戶、合作夥伴、媒體或其他非獨立來源。
- Grade E 只能作補充參考，不得支撐正式規則、分數、hard gate 或主要推薦。
- 所有案例數字只用於案例說明；不直接形成分數、權重、成功門檻、停止門檻或 hard gate，也不宣稱其他企業可重現同樣成果。

### 2.4 事實、宣稱與專案設計的邊界

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

來源包補上 11 個可接受的直接／正規化對應來源：Morgan Stanley、Klarna、BT Group、Affinda、Amazon Pharmacy、Getir、Hitachi、FIH Mobile、Zillow Offers、DoNotPay、IntelliVision（正規化 R1 的泛稱面部辨識案例）。Accenture／GitHub Copilot 來源則只用來指出 R1 將組織誤寫為 EY；EY raw entry 仍被排除。這項補充不驗證 R1 其他敘述。

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

來源包使下列 30 個案例達到「具名、可追溯來源、已知發布者與證據類型」的最低納入條件。表格只寫來源包支持的最小內容；`unknown` 不是缺漏，而是刻意防止把 raw research 的未驗證內容帶入正式案例。

共通欄位：`industry`、`country_or_region`、`why_ai_was_considered`、`poc_or_deployment_scope`、`baseline_metrics`、`risks_or_limitations`、`deployment_status`、`source_date` 均為 `unknown`，除非各列另列；所有 `planner_lessons` 都是規劃提示，不是新的 scoring 或 hard-gate 規則。

| case_id | organization | opportunity_type / solution_direction | business_problem | reported_outcomes | human_oversight | evidence_type / grade | source_name / source_url | raw research correspondence | planner_lessons |
|---|---|---|---|---|---|---|---|---|---|
| CASE-01 | Morgan Stanley | enterprise knowledge search; meeting summary / generative_ai | 內部知識與會議輔助 | vendor-reported：顧問團隊採用率超過 98%；語料約 100,000 文件 | client consent 與 advisor review（會議輸出） | vendor-reported / C | OpenAI / https://openai.com/index/morgan-stanley/ | R1 直接對應 | 驗證來源、採用與人工審閱，不採用 R1 的 20%→80% 或時間縮短數字。 |
| CASE-02 | G-STAR | internal workplace and IT knowledge assistant / unknown | 工作與 IT 知識輔助 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/25747-g-star-azure | 來源包補充；R1/R2 無具名對應 | 先問知識 owner、權限與更新責任。 |
| CASE-03 | Klarna | customer service automation / generative_ai | 客服自動化 | vendor-reported：首月 230 萬對話；平均解決時間 11 分鐘降至不足 2 分鐘；重複詢問減少 25% | `unknown` | vendor-reported / C | OpenAI / https://openai.com/index/klarna/ | R1 直接對應 | 可作 KPI 類型參考；不採用 R1 的 67%、30% 升級或年度利潤數字。 |
| CASE-04 | AIA | customer-service agent assistance / unknown | 客服坐席輔助 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/21062-aia-group-dynamics-365-customer-service | 來源包補充；僅主題對應 R1 客服 | 先定義升級與人工核可邊界。 |
| CASE-05 | BT Group and Wipro | document processing / generative_ai | 文件處理 | `unknown` | `unknown` | vendor-reported（vendor and partner）/ C | AWS / https://aws.amazon.com/partners/success/bt-group-wipro/ | R1 直接對應 | 不採用「數週變分鐘」或成本下降 25%。 |
| CASE-06 | Affinda | document extraction / generative_ai | 文件抽取 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/solutions/case-studies/affinda-case-study/ | R1 直接對應，並取代重複列 | 不採用配置／成本各下降 90%。 |
| CASE-07 | Ricoh | intelligent document processing / unknown | 智慧文件處理 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/blogs/machine-learning/how-ricoh-built-a-scalable-intelligent-document-processing-solution-on-aws/ | 來源包補充；僅主題對應 R1 文件處理 | 需樣本、欄位定義與例外處理。 |
| CASE-08 | Ironclad | contract review assistance / generative_ai | 合約審閱輔助 | `unknown` | `unknown` | vendor-reported / C | OpenAI / https://openai.com/index/ironclad/ | 來源包補充；僅主題對應 R2 合約提示 | 保留法務最終判斷。 |
| CASE-09 | Icertis | contract lifecycle and review assistance / unknown | 合約生命週期與審閱 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/1723797353687211986-icertis-professional-services-azure-openai | 來源包補充；僅主題對應 R2 合約提示 | 先確認條款標準與簽核 owner。 |
| CASE-10 | Finastra | marketing and meeting-workflow assistance / unknown | 行銷與會議工作流輔助 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/18732-finastra-microsoft-viva-engage | 來源包補充；僅主題對應 R2 行銷／會議 | 審批與品牌責任須明確。 |
| CASE-11 | Reckitt | marketing insights and localization / unknown | 行銷洞察與在地化 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/23761-reckitt-power-bi | 來源包補充；僅主題對應 R2 行銷 | 以採用率、審閱量與業務 KPI 驗證。 |
| CASE-12 | Moderna | enterprise generative-AI assistance / generative_ai | 企業生成式 AI 輔助 | `unknown` | `unknown` | vendor-reported / C | OpenAI / https://openai.com/index/moderna/ | 來源包補充；R1/R2 無具名對應 | 先將工作流切小並界定資料權限。 |
| CASE-13 | Accenture | software-development copilot / generative_ai | 開發協作 | `unknown` | `unknown` | vendor-participated research / C | GitHub / https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/ | 校正 R1 的 EY／GitHub Copilot 名稱錯置 | 不採用 R1 的 PR、合併率、CI 或 bug 數字。 |
| CASE-14 | Cisco | software-development agent / ai_agent | 工程開發 | `unknown` | `unknown` | vendor-reported / C | OpenAI / https://openai.com/index/cisco/ | 來源包補充；僅主題對應 R2 開發輔助 | 保留 review、測試與權限控制。 |
| CASE-15 | CyberAgent | software-development and knowledge-work assistance / generative_ai | 開發與知識工作 | `unknown` | `unknown` | vendor-reported / C | OpenAI / https://openai.com/index/cyberagent/ | 來源包補充；僅主題對應 R2 開發／知識 | 不由案例推定自動合併或 Agent 優先。 |
| CASE-16 | Amazon Pharmacy | demand forecasting / traditional_ml | 需求與人力預測 | `unknown` | `unknown` | vendor-reported（company ecosystem）/ C | AWS / https://aws.amazon.com/solutions/case-studies/amazon-pharmacy-case-study/ | R1 直接對應 | 不採用 MAPE 5%、10% 行業基準或節省 13%。 |
| CASE-17 | Getir | demand forecasting / traditional_ml | 需求預測 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/solutions/case-studies/getir/ | R1 直接對應 | 不採用準確度 +10% 或訓練時間 -90%。 |
| CASE-18 | Cainz | retail demand and replenishment forecasting / unknown | 零售預測與補貨 | `unknown` | `unknown` | vendor-reported / C | Google Cloud / https://cloud.google.com/customers/cainz | 來源包補充；僅主題對應 R2 預測 | 要求現況誤差、決策週期與例外流程。 |
| CASE-19 | Super-Pharm | demand and inventory forecasting / unknown | 電商需求與庫存預測 | `unknown` | `unknown` | vendor-reported / C | Google Cloud / https://cloud.google.com/customers/super-pharm | 來源包補充；僅主題對應 R2 預測 | 先建立可比較的 forecast baseline。 |
| CASE-20 | CrossTech | predictive maintenance / unknown | 鐵路預測性維護 | `unknown` | `unknown` | vendor-reported / C | Google Cloud / https://cloud.google.com/customers/crosstech | 來源包補充；R1/R2 無具名對應 | 需確認感測資料、故障定義與漏報成本。 |
| CASE-21 | ŠKODA AUTO | predictive maintenance / unknown | 產線預測性維護 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/solutions/case-studies/skoda-case-study/ | 來源包補充；R1/R2 無具名對應 | 需人工處理例外與設備安全責任。 |
| CASE-22 | Hitachi | visual quality inspection / traditional_ml | 接頭視覺檢查 | vendor-reported：PoC 約 100 張樣本圖片；描述測試的缺陷檢出率 100%；誤報率約 13% | `unknown` | vendor-reported / C | Google Cloud / https://cloud.google.com/customers/hitachi | R1 直接對應 | 僅限描述測試；不採用 R1 的一天訓練、無持續人工干預或「任何漏檢即停」規則。 |
| CASE-23 | FIH Mobile | manufacturing visual inspection / unknown | 製造視覺檢查 | `unknown` | `unknown` | vendor-reported / C | Google Cloud / https://cloud.google.com/customers/fih-mobile | R1 直接對應 | 不採用 R1 的 40%→10% 或 0.3 秒數字。 |
| CASE-24 | NSUS Group | fraud detection / traditional_ml | ML 詐欺防治 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/solutions/case-studies/nsus-group-case-study/ | 來源包補充；僅主題對應 R2 詐欺 | 不能由模型直接施加處分。 |
| CASE-25 | N26 | fraud detection / traditional_ml | 近即時詐欺偵測 | `unknown` | `unknown` | vendor-reported / C | AWS / https://aws.amazon.com/solutions/case-studies/n26-case-study/ | 來源包補充；僅主題對應 R2 詐欺 | 需要調查、覆核與誤報／漏報成本。 |
| CASE-26 | Gojob | recruiting assistance / generative_ai | 招募輔助 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/20838-gojob-azure-open-ai-service | 來源包補充；僅主題對應 R2 招聘 | 僅 assistive；不可自動淘汰。 |
| CASE-27 | Adecco Group | recruiting and workforce assistance / generative_ai | 招募與技能工作流 | `unknown` | `unknown` | vendor-reported / C | Microsoft / https://www.microsoft.com/en/customers/story/24691-adecco-group-ag-microsoft-365-copilot | 來源包補充；僅主題對應 R2 招聘 | 保留公平性檢查、人工覆核與申訴。 |
| CASE-28 | Zillow Offers | high-stakes price forecasting and automated asset acquisition / unknown | 高資本曝險的預測與資產收購 | official company disclosure：計畫停止 Zillow Offers operations；其他數字 `unknown` | `unknown` | official company disclosure / B | Zillow Group Investor Relations / https://investors.zillowgroup.com/news-and-events/news/news-details/2021/Zillow-Group-Reports-Third-Quarter-2021-Financial-Results--Shares-Plan-to-Wind-Down-Zillow-Offers-Operations/default.aspx | R1 直接對應 | 評估尾端風險、不可逆決策、資本曝險與預測不確定性。 |
| CASE-29 | DoNotPay | legal-service automation / generative_ai | 法律服務自動化宣稱 | regulator finding：FTC DoNotPay case page；其他處分細節 `unknown` | `unknown` | regulator finding / A | U.S. FTC / https://www.ftc.gov/legal-library/browse/cases-proceedings/donotpay | R1 直接對應 | 專業等同宣稱須有合格專家評估；法律輸出預設 assistive。 |
| CASE-30 | IntelliVision Technologies | biometric recognition / traditional_ml | 人臉辨識效能宣稱 | regulator finding：FTC 對其 facial-recognition claims 採取行動；具體效能數字 `unknown` | `unknown` | regulator finding / A | U.S. FTC / https://www.ftc.gov/news-events/news/press-releases/2024/12/ftc-takes-action-against-intellivision-technologies-deceptive-claims-about-its-facial-recognition | 校正 R1 泛稱面部辨識案例 | 要求分群測試、代表性資料、效能證據與覆核／申訴路徑。 |

### Raw numbers explicitly not accepted

來源包沒有支持，因而未寫入 verified outcomes 的 raw 數字包含：Morgan Stanley 的 16,000 顧問、文件存取 20%→80%、數天→數小時；Klarna 的 67% 自動化、30% 升級、年利潤 4,000 萬美元；EY／Copilot 的全部 PR、合併、CI、bug 數字；BT、Affinda、Amazon Pharmacy、Getir、FIH Mobile、WeChat Pay、匿名人壽公司與車險案例的所有數字；以及 R1 全部停止閾值。來源包沒有列出的 R2 數字也全部維持 `unknown`。

## 5. Failure, stopped, limited and regulatory cases

| Case | 已確認的來源層級 | 可保留的最小事實 | 不可從 raw research 帶入的內容 | Planner 警示 |
|---|---|---|---|---|
| Zillow Offers | official company disclosure / B | 官方投資人關係頁面說明停止 Zillow Offers operations。 | R1 的損失金額、因果與自動化流程細節。 | 高資本、不可逆決策要檢查尾端風險與回退。 |
| DoNotPay | regulator finding / A | FTC case page 存在，來源包標為 unsupported AI-lawyer claims。 | R1 的完整處分文字、具體產品流程。 | 法律輸出預設輔助，專業等同宣稱需受控驗證。 |
| IntelliVision Technologies | regulator finding / A | FTC 新聞稿 URL 存在，來源包標為 facial-recognition claims。 | R1 的泛稱描述與任何未列的偏差／準確率數字。 | 生物辨識需分群證據、人工覆核與申訴。 |
| IBM Watson for Oncology | 無來源 / E | `unknown` | R1 的不安全治療主張與人工流程。 | 僅能保留為待重新搜尋的高影響醫療提醒。 |
| Amazon 招聘模型 | 無來源 / E | `unknown` | R1 的偏向男性、停止使用與人工流程主張。 | 僅能保留為待重新搜尋的高影響招聘提醒。 |

上述僅提出 hard-gate 候選的討論方向，不能在本輪新增或調整任何 hard-gate 規則。

## 6. Rejected or weak evidence

| 類別 | 來源位置／案例 | 排除原因 | 可否作一般背景 |
|---|---|---|---|
| anonymous | R1 未透露客服、未披露會議紀要 | 組織不具名，來源包也明確排除。 | 僅一般場景提示。 |
| unclear organization | R1 法律／金融／醫療／HR／醫院／營運團隊、某大型人壽保險公司、中科萬國車險 | 不是來源包中可恢復的具名組織。 | 否。 |
| duplicate | R1 Affinda 第二列 | CASE-06 已保留一個來源包對應；第二列不再算案例。 | 否。 |
| unmatched raw name | R1 WeChat Pay；R2 Tapestry、Orion Health、LUXGEN、Max Life、Sun Finance、Condé Nast、Huge、Papel Semente、Globe Telecom、EVERSANA、beBit、ComplyAdvantage、CME、Valeo、Clodura、Randstad、OTTO、Tchibo、Mastercard、Ubidy、1111 | 來源包未提供這些名稱可追溯來源；R2 `turn…` 引用仍不可恢復。 | 僅作未驗證搜尋線索。 |
| raw-name mismatch | R1 EY／GitHub Copilot | 來源包只支持 Accenture／GitHub Copilot；R1 的 EY 組織與數字不被接受。 | 可保留「開發輔助」場景，不保留個案數字。 |
| no supported metric | 除 CASE-01、03、22 來源包明確點名的 page claims 外的全部成功案例 | URL 與案例存在不等於 raw 指標被支持。 | 可作 KPI 類型靈感，不能引用數字。 |
| unsourced threshold | R1 95%、2%、10%、80%／90% 等停止門檻 | 來源包沒有支持。 | 否，不得轉為規則。 |
| report-generated inference | R1「確定性規則清單」；R2 權重與 five gates 建議 | 屬作者歸納或專案設計提案。 | 可供人工討論。 |
| unrelated to Planner scope | R1 Mermaid 的開發、部署、模型訓練流程 | Planner 不負責實作或部署。 | 否。 |

## 7. Candidate AI opportunity types

以下是人工核准的正式 AI opportunity catalog 範圍，不是 JSON、Pydantic model 或 deterministic matcher。`related_verified_cases` 僅列來源包案例 ID；多數為 Grade C 的 vendor-reported evidence，不能把成果數字轉為規則。`software_development_assist` 已移出正式 catalog。

| opportunity_id / name | business_problem_signals；suitable / unsuitable | minimum_information_needed；clarification_questions | candidate_solution_directions；recommended_human_involvement | candidate_poc_kpis；pause_or_stop_signals | related_verified_cases；search_keywords |
|---|---|---|---|---|---|
| enterprise_knowledge_and_professional_document_assist / 企業知識與專業文件輔助 | 知識散落、需理解專業文件或提示合約／法律風險；不適合替代專業最終判斷。 | 文件來源、權限、更新 owner、專業審查標準；「答案須附依據嗎？誰最後核定？」 | generative_ai 或 hybrid；高風險／專業文件必須人員輔助。 | 帶來源回答率、找答案時間、人工採用／更正率；權限、owner 或專業簽核不清時暫緩。 | CASE-01, CASE-02, CASE-08, CASE-09；knowledge query, professional document assist. |
| customer_service_assist / 客服輔助 | 大量重複詢問、需升級複雜案件；不適合自動做補償或法律承諾。 | FAQ、政策、升級規則、現況 CSAT／處理時間；「何時轉人工？」 | generative_ai 或 hybrid；中至高。 | 首問解決、處理時間、正確升級率、CSAT；政策頻繁變更且無維護時暫緩。 | CASE-03, CASE-04；customer service escalation. |
| document_classification_and_extraction / 文件分類與資料抽取 | 文件分類、欄位擷取、重複登打；不適合樣本不可取得或欄位持續變動。 | 樣本、欄位定義、對照答案、敏感資料界線；「例外誰處理？」 | traditional_ml、generative_ai 或 hybrid；低置信度人工覆核。 | 欄位正確率、人工複核率、處理時間；無合法樣本或無例外流程時暫緩。 | CASE-05, CASE-06, CASE-07；document classification, extraction. |
| meeting_summary_and_action_items / 會議摘要與行動項 | 會議紀錄延遲、行動項遺漏；不適合不能錄音或極敏感會議。 | 錄音／逐字稿、摘要格式、保留政策；「誰確認 owner 與期限？」 | generative_ai；低至中。 | 行動項正確率、採用率、整理時間；轉錄品質不足或無使用授權時暫緩。 | CASE-01, CASE-10；meeting summary, action items. |
| marketing_content_assist / 行銷內容輔助 | 文案變體與審稿量大；不適合沒有品牌／法遵審核就自動發布。 | 品牌規範、禁語、審核流程、目標指標；「誰批准發布？」 | generative_ai；中至高。 | 草稿到批准時間、退稿率、編輯量、轉化指標；審批責任不清時暫緩。 | CASE-10, CASE-11, CASE-12；marketing content. |
| demand_forecasting / 需求預測 | 補貨、排班、產能預測失準；不適合資料短缺或口徑不一致。 | 時序資料、決策週期、外生變數、目前誤差；「誤差造成什麼成本？」 | traditional_ml、data_analytics；例外人工確認。 | MAPE／WAPE、缺貨、庫存周轉、浪費；沒有現況誤差基準時暫緩。 | CASE-16–CASE-19；demand forecasting. |
| predictive_maintenance / 預測性維護 | 設備故障與停機成本高；不適合沒有可用感測或維修資料。 | 感測資料、故障定義、維護流程、漏報成本；「何時由維修人員覆核？」 | traditional_ml、data_analytics；維修決策由人員確認。 | 提前預警時間、漏報、誤報、停機時間；資料不連續或安全責任不清時暫緩。 | CASE-20, CASE-21；predictive maintenance. |
| anomaly_and_risk_detection / 異常與風險偵測 | 影像缺陷、交易異常或其他可量化異常；不適合沒有標註、調查容量或錯誤成本定義。 | 資料模態、異常定義、標註、誤報／漏報成本、回饋；「誰調查、覆核與處置？」 | rule_based_automation + traditional_ml，必要時 generative_ai 輔助摘要；高。 | 依模態分別定義：影像看漏檢／誤檢／速度，交易看 precision／recall／FPR／調查週期；直接處罰或無覆核時 block。 | CASE-22–CASE-25；visual anomaly, fraud detection. |
| recruiting_process_assist / 招聘流程輔助 | JD、履歷摘要、排程耗時；不適合自動淘汰或錄用。 | 職能模型、流程、合規 owner、人工覆核與申訴；「系統會否影響錄用？」 | generative_ai、data_analytics；高，assistive-only。 | 招募作業時間、人工一致性、候選人體驗；無人工覆核／申訴或直接篩除時 block。 | CASE-26, CASE-27；recruiting process assist. |

### Approved non-AI alternative directions

下列三者不是正式 AI opportunity types；Planner 應在適當時將它們列為替代方向：

| direction | 適用提示 |
|---|---|
| `rule_based_automation` | 規則明確、輸入輸出固定、例外少。 |
| `conventional_software` | 問題主要是表單、權限、資料庫、通知、流程或系統整合。 |
| `data_analytics` | 目標是理解現況、趨勢、分群、異常或原因，而不是自動做預測或決策。 |

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

## Deployment posture assessment

雲端、私有環境、地端與混合部署不是 opportunity type，而是每個候選方案必須經過的橫向規劃分析。本節只提供候選方向、限制、成本形態與待確認事項；不選定雲端供應商、模型產品、硬體型號或實際報價。

### Candidate directions

| deployment posture | 適合條件 | 限制與待確認事項 | cost shape |
|---|---|---|---|
| `public_cloud_managed` | 快速 PoC、初期成本較低、使用量不確定、缺少內部模型維運能力，且資料允許外部受控處理。 | 確認資料處理、保留、訓練、網路與資料落地條件。 | 前期投入低；多為浮動成本；使用量成長有成本風險；維運負擔較低。 |
| `private_cloud_or_isolated_environment` | 需要網路隔離、區域限制或企業治理，且已有雲端基礎設施。 | 確認隔離邊界、區域、存取控制、審計與內部維運能力。 | 前期投入中；固定與浮動成本並存；維運負擔中至高。 |
| `on_premises` | 必須完全離線、資料不得離開內網、高度機密或特殊合規，使用量穩定且已有硬體與維運能力。 | 確認容量、更新、資安、備援、模型與平台維運責任。 | 前期投入高；固定成本較高；浮動成本較低；維運負擔高。 |
| `hybrid` | 敏感與非敏感資料並存、原始資料要留在地端，或可將去識別化／低敏感工作交由雲端。 | 確認資料切分、去識別化、跨環境傳輸、整合與責任界線。 | 前期投入中至高；固定與浮動成本並存；整合與維運負擔較高。 |

不得把「敏感資料」簡化為必然地端，也不得把「成本較低」無條件等同公有雲。

### Structured inputs

| 面向 | 結構化輸入 |
|---|---|
| 保密與合規 | `data_classification`、`contains_personal_data`、`contains_trade_secrets`、`contains_regulated_data`、`data_residency_required`、`external_processing_allowed`、`provider_data_retention_allowed`、`provider_training_on_data_allowed`、`internet_access_allowed` |
| 成本與用量 | `expected_request_volume`、`expected_concurrency`、`workload_variability`、`expected_context_or_file_volume`、`latency_requirement`、`availability_requirement`、`budget_preference`、`existing_gpu_or_server_capacity` |
| 維運與環境 | `existing_cloud_environment`、`existing_on_prem_infrastructure`、`internal_ai_operations_capability`、`model_update_requirement`、`integration_constraints`、`vendor_lock_in_tolerance`、`offline_operation_required` |

`data_classification` 初期只可使用：`public`、`internal`、`confidential`、`highly_confidential`、`unknown`。

### Responsibility boundary

| 元件 | 責任 |
|---|---|
| LangChain／LLM | 從自然語言抽取保密、成本、既有環境與離線需求；找出未知欄位；產生澄清問題；解釋部署候選方向。不得直接決定最終部署姿態。 |
| Deterministic deployment posture rules | 排除不允許的部署方向；根據結構化欄位產生候選與理由；比較初期成本、浮動成本、資本投入與維運負擔；列出關鍵假設與缺失資訊。 |
| Hard-gate engine | 處理法規禁止資料離境、外部處理不允許、必須完全離線、高度機密資料缺少核准環境，以及必要審計、存取控制或資料治理缺失。 |

部署 hard gate 應優先排除不合格的**部署方式**；只要仍有地端或混合等合格替代方案，就不應直接阻擋整個 AI PoC。

### Required Planner output

每個候選 opportunity 應可附帶下列規劃輸出：

- `recommended_deployment_posture`
- `acceptable_alternatives`
- `disallowed_or_not_recommended_options`
- `confidentiality_and_compliance_reasons`
- `cost_shape`：只描述前期投入高低、固定或浮動成本、使用量成長風險與維運負擔。
- `operations_requirements`
- `critical_assumptions`
- `missing_deployment_information`
- `poc_deployment_recommendation`

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
| EV-05 | 根據產線照片提示可能瑕疵。 | traditional_ml | hybrid | anomaly_and_risk_detection | 圖片、標註、漏檢成本 | 低置信度覆判 | 漏檢、誤檢、速度 | 相機不穩或無樣本 | generative_ai 作首選 | CASE-22, CASE-23 |
| EV-06 | 回答員工制度與 SOP 問題並附來源。 | generative_ai | hybrid | enterprise_knowledge_and_professional_document_assist | 文件、權限、owner | 高風險答案確認 | 帶來源率、找答案時間、採用率 | 權限或更新機制不清 | 自動執行人事／財務動作 | CASE-01, CASE-02 |
| EV-07 | 協助客服摘要案件與建議回覆。 | generative_ai | hybrid | customer_service_assist | 政策、升級規則、CSAT baseline | 客服核可；補償／投訴升級 | AHT、CSAT、升級正確率 | 無轉人工邊界 | 無監督自動承諾 | CASE-03, CASE-04 |
| EV-08 | 抽取發票欄位並送入人工複核佇列。 | hybrid | traditional_ml | document_classification_and_extraction | 樣本、欄位定義、PII 規則 | 低置信度與例外覆核 | 欄位正確率、複核率、時間 | 資料不可合法使用 | 無校驗直接入帳 | CASE-05–CASE-07 |
| EV-09 | 幫法務標記合約紅旗條款。 | generative_ai | hybrid | enterprise_knowledge_and_professional_document_assist | 條款庫、紅旗定義、簽核權責 | 律師最終決策 | 召回、誤報、審閱時間 | 無法務 owner | 自動法律結論／核准 | CASE-08, CASE-09 |
| EV-10 | 讓 AI 直接淘汰履歷並決定錄用。 | blocked | assistive-only | recruiting_process_assist | 合規、偏差檢查、申訴、人工流程 | 人工最終決策必須存在 | 作業時間、人工一致性 | 自動篩除或無申訴 | 自主錄用／淘汰 | CASE-26, CASE-27 |
| EV-11 | 用交易資料找可疑案件，直接凍結帳戶。 | assistive-only | traditional_ml + rules | anomaly_and_risk_detection | 標註、損失、覆核量能 | 調查人員最終處置 | precision、recall、FPR | 直接處罰或無覆核 | 自主制裁 | CASE-24, CASE-25 |
| EV-12 | 做跨採購、人資、財務系統的「萬能 Agent」。 | more_information / staged | 拆分後的 generative_ai 或 conventional_software | `unknown` | 目標、權限、動作清單、批准點 | 每個高風險動作批准 | 任務完成、人工 override、錯誤成本 | 範圍過大、權限不清 | 直接推薦 ai_agent 上線 | `unknown` |
| EV-13 | 老闆要求「我們也要 AI」，但沒有問題、資料或 owner。 | do_not_use_ai / pause | conventional_software | `unknown` | 業務目標、owner、成功定義 | 人工先定義需求 | `unknown` | 核心資訊缺失 | 任何 AI 方案 | `unknown` |
| EV-14 | 會議後自動整理摘要與待辦。 | generative_ai | conventional_software | meeting_summary_and_action_items | 錄音授權、格式、敏感性 | owner 確認待辦 | 採用率、待辦正確率、時間 | 無授權或轉錄不可靠 | 自動外傳敏感內容 | CASE-01, CASE-10 |
| EV-15 | 讓開發者產生測試與文件，但保留 PR review。 | out_of_catalog | `unknown` | `unknown` | repo 範圍、測試、資安規則 | 工程師 review／merge | `unknown` | 不屬正式 catalog 範圍 | 正式 catalog 推薦 | CASE-13–CASE-15（案例參考，非 catalog） |

## 11. Recommendation for M2.3-lite

1. **正式 catalog 範圍：** 已人工核准九類：`enterprise_knowledge_and_professional_document_assist`、`customer_service_assist`、`document_classification_and_extraction`、`meeting_summary_and_action_items`、`marketing_content_assist`、`demand_forecasting`、`predictive_maintenance`、`anomaly_and_risk_detection`、`recruiting_process_assist`。案例支援「案例連結與規劃提示」層；多數為 Grade C，不能支持固定成效保證。
2. **非 AI 與非 catalog 邊界：** `rule_based_automation`、`conventional_software`、`data_analytics` 是已核准的非 AI 替代方向，不是 opportunity types。`software_development_assist` 已移出正式 catalog；AI Agent、銷售線索分析與資料儀表板也不在本輪正式 catalog 範圍。
3. **適合 deterministic matching 的欄位：** 業務問題信號、資料是否存在、輸入／輸出是否固定、是否需要預測、是否是非結構化文字／文件、是否需要多步工具、權限是否清楚、部署動作是否可逆、已知高影響領域、baseline 是否存在。
4. **適合 LangChain／LLM 的欄位：** 模糊需求理解、業務目標歸納、結構化意圖抽取、澄清問題生成、候選方向說明、報告敘述整理；不得由 LLM 決定正式分數、gate 或唯一 recommendation。
5. **必須由 deterministic scoring engine 決定的內容：** 六維評分、權重套用、分數理由的結構、缺失資訊處理與 recommendation 排序。
6. **必須由 hard-gate engine 決定的內容：** 高風險決策邊界、assistive-only、人工最終決策要求、暫緩或 block。這是既有專案契約，非本研究新增規則。
7. **只能作參考、不得成為規則的內容：** R1／R2 所有案例數字、百分比、節省金額、準確率、停止門檻與權重提議。
8. **是否建議進入 M2.3-lite implementation：** catalog 範圍、evidence policy、deployment posture 欄位與責任邊界均已人工核准；在 PR #3 合併且 `main` 同步後，可依既有依賴順序開始 M2.3-lite。本輪仍不開始程式實作。
9. **實作前仍需人工確認：** Grade C 案例的公開呈現方式與 vendor-reported 標籤、source URL 的更新／失效處理、評估案例是否要正式化為測試資料，以及既有 scoring／hard-gate 與 catalog、deployment posture 欄位的契約對應。

### 責任邊界

| 元件 | 責任 |
|---|---|
| LangChain／LLM | 理解模糊需求、歸納目標、抽取結構化意圖、生成追問、解釋候選方案、整理報告。 |
| Catalog matching | 將結構化意圖對應 1–3 個候選 opportunity types，提供候選方向、追問、KPI 與參考案例；不決定最終 recommendation。 |
| Deterministic scoring engine | 六維評分、權重、分數說明、缺失資訊與 recommendation 排序。 |
| Hard-gate engine | 高風險決策邊界、assistive-only、人工最終決策、暫緩或 block。 |

## Human review decision

- 九類正式 opportunity catalog 已核准：`enterprise_knowledge_and_professional_document_assist`、`customer_service_assist`、`document_classification_and_extraction`、`meeting_summary_and_action_items`、`marketing_content_assist`、`demand_forecasting`、`predictive_maintenance`、`anomaly_and_risk_detection`、`recruiting_process_assist`。
- 三類非 AI 替代方向已核准：`rule_based_automation`、`conventional_software`、`data_analytics`。
- Evidence policy 已核准：A／B／C 是較強參考；D 可顯示為真實案例但必須標示非獨立來源；E 僅作補充參考。
- Catalog matching 的邊界維持先前決定：只對應 1–3 個候選方向，提供追問、KPI 與案例參考；不決定六維分數、最終 recommendation 或 hard gate。
- Deployment posture assessment 是 M2.3-lite 與後續 Planner 的必要需求；它是橫向規劃分析，不是 opportunity type。
- 案例數字只用於案例說明，不得轉為正式規則、分數、權重、成功／停止門檻或 hard gate，亦不得宣稱可被其他企業重現。

## Audit counts

| 項目 | 數量 |
|---|---:|
| R1 raw 表格案例項目 | 27 |
| R2 raw 具名案例提及 | 24 |
| Raw case entries 合計（未去重） | 51 |
| 來源包具名且可追溯的 verified source cases | 30 |
| 來源包 Grade A / B / C / D / E | 2 / 1 / 27 / 0 / 0 |
| Raw entries 經來源對應後的 Grade A / B / C / D / E | 2 / 1 / 8 / 0 / 40 |
| 成功直接或經組織名稱正規化的 raw case 對應 | 11 |
| 來源包補充、但不倒填 raw research 的 verified source cases | 19 |
| R1 失敗、停止、受監管或效果有限案例 | 5 |
| 可用於正式 deterministic rule 的 raw case 數字 | 0 |
