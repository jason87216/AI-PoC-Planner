# AI PoC Planner Case Study

## 專案摘要

AI PoC Planner 是一個本機優先的企業 AI 導入需求分析與 PoC 規劃工具。它處理的不是「請模型直接給答案」，而是把模糊需求整理成可確認的事實、可比較的方案、可追溯的治理判斷，以及可下載的規劃報告。

這個作品集展示使用一次已完成的真實產品流程：需求理解、使用者確認、有界訪談、Assessment、Results、Markdown download 與 History re-entry。模型負責理解與敘事，正式 matching、評分、hard gates 與 recommendation 由 deterministic code 決定。

## 問題與使用者

企業通常只有一句「想用 AI 改善流程」的模糊構想，卻缺少可確認的需求、責任邊界、方案比較、風險 gate 與 PoC 驗收條件。若直接讓模型產生方案，容易把未確認的假設誤當成正式結論，也難以說明為什麼某個推薦可以成立。

主要使用者包括企業業務負責人、PoC／轉型負責人、主管、系統負責人、資料負責人與資訊安全審核人員。產品 owner 可以是企業資訊治理或資訊安全團隊；工程與 AI workflow 團隊則能透過持久化結果檢視證據與決策邊界。

## Canonical Demo

本作品集的 canonical synthetic demo 是「企業權限申請與風險審查 AI PoC」。所有展示資料都是 synthetic data，不是任何真實員工或客戶的權限資料。

情境中，員工透過表單申請內部系統與敏感資料的存取權限；主管、資料負責人與資訊安全人員需要檢查申請理由、職務需求、資料敏感程度與最小權限原則。AI 可以協助整理申請內容、辨識缺漏、比對政策並產生風險摘要，但不得自行批准申請、直接修改正式權限，或把敏感資料傳送到未核准的外部服務。

## 完整使用流程

```text
最小 brief
  → AI requirement understanding
  → 使用者修正／確認
  → bounded interview
  → confirmed facts
  → deterministic matching 與 Assessment
  → 六維評分與 hard gates
  → Results 與 persisted Markdown report
  → History re-entry／download
```

每一個階段都有明確邊界：需求理解可以提出候選整理，但正式分析必須使用已確認的資料；訪談有輪數上限；Assessment 只使用通過驗證的 persisted analysis；完成版本不可原地覆寫。

## 系統架構

```text
Streamlit UI
    ↓
FastAPI public API
    ↓
Application services
    ├─ Structured-output executor → OpenAI-compatible adapter → selected provider
    ├─ Deterministic matching / scoring / hard gates
    └─ SQLite project / version / conversation / analysis / report
```

Streamlit 只透過 FastAPI 取得產品資料。provider adapter 是真實模型傳輸邊界；typed structured output 先通過 schema 與 Pydantic 驗證，再進入 application semantic validation。SQLite 保存 project、immutable version、可見對話、confirmed facts、PlanningRun、assessment 與 report，讓 Results、History 與 Markdown download 使用同一份正式結果。

產品目前使用單一 OpenAI-compatible adapter，不宣稱支援所有相容端點，也沒有多 provider business logic。LangChain 用來整合模型呼叫與結構化輸出流程；產品沒有使用 LangGraph 或多 Agent 編排。

## LLM 與 Deterministic Code 的責任邊界

LLM 負責：

- 理解模糊企業需求；
- 提出有理由且有界的訪談問題；
- 整理候選 facts、假設、矛盾與缺漏；
- 產生受 schema 約束的候選方案與 report narration。

Deterministic code 負責：

- opportunity、solution 與 reviewed-case matching；
- recommendation category 與正式 solution；
- 六維評分與加權總分；
- hard gates、decision authority 與 processing boundary；
- fact reference、solution／case／project consistency；
- persistence transaction 與 immutable version transition。

Provider 的候選值不能覆寫正式 recommendation、權重、總分、gate disposition、catalog 事實或權限動作。這個邊界讓模型可以提供有用敘事，同時讓正式結果可以被測試、追蹤與重新載入。

## Discovery 與有界訪談

Discovery 先把 brief 轉成使用者可檢查的 requirement understanding。使用者可以修正或確認內容；確認後，系統才進入最多三輪的 bounded interview。每個問題會說明為什麼重要、會影響哪個判斷，並保留 `不知道` 或目前沒有相關資料的狀態。

這種設計避免兩個問題：模型不能用無限追問拖延流程，也不能把沒有被使用者確認的假設直接當成正式 evidence。訪談結果會保存為可見對話與 confirmed facts，後續 analysis 只讀取通過驗證的資料。

## Assessment、六維評分與 Hard Gates

Assessment 會比較 AI、規則、自動化、傳統軟體或 foundations-first 等相關方向，並以 reviewed catalog 與 confirmed project facts 做 deterministic matching。六維評分涵蓋商業價值、資料可用性、技術裝備性、架構可控性、治理程度與使用者採用度；每個維度保留判斷、依據、改善條件與資料缺口。

Hard gates 用來阻止不符合治理邊界的路線，例如未經授權的資料使用、AI 自主作出高影響決策、未核准外部處理、缺少必要的人工作業或直接寫入正式權限系統。Gate 可以允許 local、assistive、deterministic 或 human-reviewed 的第一階段 PoC，但不能被模型覆寫。

## Report 與持久化

Results 使用同一份已保存的 analysis、scores、gates、reviewed cases 與 report synthesis。完成版本是 immutable；若要修改，產品建立新的 version，而不是覆寫原始結果。

canonical demo 已完成一次正式 report 流程，並驗證：analysis 1 筆、3 個方案、6 個維度分數、4 個 gates、1 份 persisted report、Markdown download 成功，以及從 History 重新進入 completed Results。History reload 與 download 讀取已保存結果，不重新呼叫 provider。

## 安全與治理設計

- 正式分析只使用專案綁定、啟用且 readiness test 通過的 model profile。
- 不使用 silent fallback；fake provider 只存在於 deterministic automated tests。
- API key 目前保存於本機 private `model_profiles.json`，這是 MVP 邊界，不是 production-grade credential storage。
- SQLite、public API、UI 與 Markdown 不保存 API key、Authorization header、prompt、reasoning trace 或 raw provider response。
- 正式 UI 不顯示 UUID、run ID、base URL、SQLite path 或 raw JSON。
- 敏感權限情境保留 human final decision，AI 不直接批准或寫入正式權限系統。

## 工程實作重點

1. **把候選敘事與正式結果分離。** Provider DTO 可以描述方案，但 application 會重新從 confirmed facts、catalog 與治理規則建立正式結果。
2. **讓錯誤可安全重試。** Structured output、semantic validation、fact reference 與 consistency failure 都在 persistence 前 fail closed，不保存 partial report。
3. **以 immutable version 支援追溯。** 每個完成版本保留對話、facts、analysis 與 report；History 可以重新開啟同一結果，不產生額外模型成本。
4. **將本機 runtime 當成產品邊界。** Windows quickstart 只負責隔離 `.venv`、選擇安全埠、監督 FastAPI／Streamlit 與安全停止，不安裝 provider 或模型。

## 測試與驗證

離線驗證基線為 `889 passed`，7 個 live-provider tests 預設 skipped，CI 已通過。fake provider 只用於可重現的自動化測試；真實 provider UAT 是明確 opt-in，不是 CI 的 secret dependency。

另以真實產品 UI 完成 canonical synthetic demo 的一次流程，確認需求理解、bounded interview、Assessment、report、Markdown download 與 History re-entry。作品集圖片是產品畫面證據，不把圖片本身宣稱為 automated test。

## 技術取捨

- 選擇單一 application service flow，而不是多 Agent；主要價值在清楚的責任邊界與可驗證的 state transition。
- 選擇 SQLite，因為本產品是 local-first、single-user MVP，需要簡單、可持久化、可重開的 project/version state。
- 使用受審核的 reviewed-case catalog，而不是即時搜尋，讓來源、適用 solution key 與限制可以被審查。
- 使用 LangChain 協助模型與 structured output 整合，但不把 business rules 藏進 prompt。
- 將 credential storage 留在 private local profile，是目前可運作的 MVP 邊界；企業化部署仍需要受控 secret store。

## 已知限制

- P7.2b 的四個 golden scenarios 完整雙端點 compatibility matrix 尚未完成；P7.2 overall 仍是 incomplete。
- 沒有 consumer installer、cloud deployment、multi-tenancy、PDF／DOCX export 或 provider/model 自動安裝。
- 本機 `model_profiles.json` 的 API key 仍是明文保存，尚未達到 production-grade credential storage。
- reviewed cases 是受審核的靜態 catalog，不等同於即時企業市場研究或自動化案例搜尋。

## 未來方向

下一步會先完成 P7.2b 的 bounded compatibility matrix 與產品／技術驗收，再評估 production-grade credential store、consumer installer、雲端部署與更完整的 evaluation telemetry。這些方向都必須保留 deterministic governance、human final decision 與 no-silent-fallback 的邊界。

## 畫面導覽

以下六張圖片是本案例的實際產品 UI：

1. [完整 Results 與推薦摘要](assets/01-results-hero.png)：顯示正式 recommendation、結果摘要與 Markdown download 入口。
2. [AI 需求理解](assets/02-requirement-understanding.png)：顯示模糊需求如何被整理成可確認的結構。
3. [Bounded interview](assets/03-bounded-interview.png)：顯示訪談完成與 confirmed requirements。
4. [Assessment comparison](assets/04-assessment-comparison.png)：顯示三個方向、成熟案例與差異比較；其中公開 reviewed cases 僅作為已審核的來源脈絡。
5. [Hard gates 與六維評分](assets/05-hard-gates-and-cases.png)：顯示治理限制、改善條件與 human review 邊界。
6. [History re-entry](assets/06-history-and-report.png)：顯示 completed synthetic project 可重新開啟，且不重新呼叫 provider。

本文件與圖片是 Portfolio Showcase Package，不新增產品 roadmap phase，也不改變 P7.2b Pending 的狀態。
