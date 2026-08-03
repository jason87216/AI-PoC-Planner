# Project Log

## Current status

### P7.2a closeout — passed

- Final dual-endpoint `governed_access` UAT was executed exactly once, without retry, in the cost-safe order `llama_cpp → remote NVIDIA endpoint`.
- Both endpoints completed readiness, discovery, analysis, and report with the same OpenAI-compatible adapter and exact JSON Schema mode; `fallback_used=false` throughout.
- Both endpoints produced three analysis options. Analysis used `analysis_options_a0` at 1024 tokens and three `analysis_option_detail` calls at 2048 tokens; report Part A and Part B each used 2048 tokens. All successful attempts were first-pass and report semantic pass was `[1]`; deterministic degradation fallback was not invoked.
- Normalized deterministic results were equal: `matching_status=matched`, `no_case_reason=null`, `recommendation_category=rules_first`, `decision_authority=human_final_decision`, `processing_boundary=private_endpoint`; reviewed cases were non-empty and unique (`case-08`, `case-09`, `case-10`). Required phases and gates remained unchanged, and all autonomous-approval, direct-write, unapproved-PII, and high-risk-provisioning safeguards remained false.
- Duplicate/read-only operations, reload, history re-entry, Markdown download, restart, persistence checks, and secret-safety checks passed for both endpoints. Sanitized evidence is retained outside this repository without provider content or secrets.
- P7.2a compatibility checkpoint passed. P7.2b remains pending; the overall P7.2 initiative is not complete.

### P8.1a portfolio baseline — Complete

- P8.1a 以文件與作品集素材為範圍，不修改 application behavior、provider implementation、deterministic logic、database schema 或 dependencies。
- README 已補充產品定位、使用者、五分鐘啟動、model-profile readiness、synthetic `governed_access` Demo 與 AI／deterministic boundary。
- `docs/portfolio/P8_1_PORTFOLIO_BASELINE.md` 提供架構圖、workflow、P7.2a 脫敏 evidence 摘要、截圖清單、技術亮點與 limitations。
- `governed_access` 明確標示為作品集 synthetic fixture，不是真實公司員工或權限資料。
- 文件已明確說明 profile 由模型設定頁建立、編輯、測試與選擇，目前沒有 profile import／export UI。
- 文件已明確揭露 MVP API key 會以明文保存於本機 private `model_profiles.json`；它不進 public API、SQLite 正式資料、logs 或 Markdown，production-grade secret store 仍 deferred。
- 文件已明確界定 capability contract 只支援 OpenAI-compatible `/v1/chat/completions` 與 `none`／Bearer authentication，不宣稱支援所有相容端點。

### P8.1b-1 Traditional Chinese UI wording and product guidance — Complete

- 模型設定、能力選擇、模型可用性測試、需求訪談、評估、報告與歷史頁面已補上繁體中文產品引導；
- 明確說明 AI 只協助理解與整理，正式推薦、分數與硬性限制仍由 deterministic 程式規則負責；
- 無可用模型、連線失敗與可重試錯誤維持 fail-closed，並提供安全、可行動的下一步；
- capability label 保留穩定 wire value，UI 不依品牌或模型名稱猜測端點能力；
- 只完成 UI 文案、presentation helper、相關測試與 offline validation，未修改 API、provider、SQLite schema、deterministic logic 或 dependencies。
- P8.1b-2 product-owner and release acceptance 仍 Pending；P8.1b overall 仍 Pending；P7.2b 仍 Pending；P7.2 overall 仍 incomplete。

### P8.1b-2 product-owner and release acceptance — Pending

- 人工驗收發現兩項 blocking defects：舊版 SQLite schema 仍可能讓 runtime 宣稱 running，以及模型設定頁把目前設定、新增、編輯與技術欄位塞在同一個長頁面。
- 本修正拆分模型設定首頁、新增頁與編輯頁，將 capability 技術值收進「相容性設定（技術人員）」；既有 API field names 與完整 payload 仍相容，但 InitialBrief requiredness 已放寬，四個補充欄位可為 null／missing，名稱與目前流程仍必填。
- provider wire contract 與 deterministic result contract 未變。
- 本修正讓 runtime 在 ready 前完成 SQLite initialization、migration 與 schema validation；migration 失敗時 fail closed，公開錯誤只提供可行動的本機資料庫指引。
- 新建專案現在只要求專案名稱與目前流程與問題；其他四項 brief 欄位可留白並正規化為 missing facts，交由後續訪談補齊。
- 人工 UAT 另發現兩項 blocking defects：訪談 widget key 未包含 project/version/round/question，造成跨輪答案殘留；assessment 的 deterministic facts 組裝 `ValidationError` 未在 `EvidenceAnalysisService` 邊界包裝，曾落成 generic `internal_error`。
- 本修正以完整情境 key builder、互斥 answer/unknown/missing 狀態與 fail-closed `analysis_result_invalid` 安全錯誤處理；不保存 partial analysis，版本維持 `ready_for_assessment`，可安全重試且不重跑已完成訪談。
- 最終獨立審查另發現 Streamlit `st.form` 內使用輸入 widget callbacks；本修正改用單一 radio（提供回答／目前不清楚／目前沒有相關資料）與 scoped text area，表單只保留 submit callback，並以 AppTest 驗證實際訪談頁可渲染、跨輪與跨專案狀態隔離。
- 新增 temporary SQLite analysis failure integration test：invalid domain assembly 不產生 partial row、訪談資料保留、版本維持 `ready_for_assessment`，修正 fake output 後可再次提交成功；UI 錯誤文案改為中立的「評估結果格式無法驗證」。
- P8.1b-2 仍待重新人工驗收；P8.1b overall、P7.2b 與完整 P7.2 仍未完成。

### P8.1b-2 renewed manual UAT follow-up — Pending

- The next bounded follow-up stops re-asking unknown/missing interview topics, combines analysis and report generation into one explicit user action, and keeps analysis/report persistence transitions separate.
- Report references are now solution-scoped; empty reviewed-case sections are omitted with a safe explanatory message, and the generic roadmap distinguishes pre-scale review from the PoC phase.
- This remains offline implementation work pending renewed manual acceptance; P7.2b remains pending and P7.2 overall remains incomplete.

### Historical diagnosis

The earlier readiness, analysis-budget, report-contract, and persistence-compatibility investigations are retained below as historical context; the closeout above is the current status.

- PR #24 已合併至 `main`。
- Merge commit：`91bb6b45f9be2249d9cd9edfd11a309bd806f321`。
- P6.7 已完成。
- Results narrative、reviewed-case catalog consistency 與 report persistence 已通過產品驗收。
- P7.1 本機 UAT runtime 已完成並維持目前啟動／停止基線。
- Historical goal：P7.2a provider compatibility and structured-output policy（PR #26，Draft）。
- 第二次 NVIDIA／llama.cpp live UAT 已執行一次：NVIDIA governed_access 完整流程
  先執行且未出現 assertion failure，但 llama.cpp readiness 以安全錯誤
  `provider_timeout` 失敗。相同 adapter contract 在 60 秒 timeout 下於本機
  22.178 秒成功；health 與 model discovery 亦通過，診斷指向原本 10 秒 readiness
  timeout 過短；當時尚待 dual-endpoint closeout。
- 本輪修正將 readiness timeout 預設為 60 秒、允許 process-level 設定至 300 秒，並讓
  llama.cpp 完整 compatibility gate 先於 remote NVIDIA endpoint workflow；尚未安排新的 live UAT。
- 第三次 dual-endpoint live UAT 已執行一次：llama.cpp readiness 失敗，local-first gate
  正常阻止 NVIDIA 呼叫，因此 NVIDIA call count 為 0；沒有通過的 dual-endpoint artifact。
- 後續 sanitized 本機 response-structure diagnosis 顯示：模型確實回傳 JSON object，但
  `status` 不符合 `Literal["ok"]`；1024 tokens 消除了其中一次 truncation，仍未修正
  contract；`--reasoning off` 也回傳錯誤 contract。timeout 不再是目前根因，沒有安排
  第四次 dual UAT。
- 本輪實作將 readiness 首輪 instruction 固定為單一 `status="ok"` JSON contract，並讓
  bounded repair hint 安全列出 Literal／enum allowed values；當時尚待 dual-endpoint closeout。
- Exact OpenAI JSON Schema readiness 已連續 3/3 通過，Discovery 已達
  `ready_for_assessment`；完整本機 workflow 在第二個 `analysis_option_detail` 失敗，兩次
  都以 `finish_reason=length` 用滿 1024 completion tokens。Schema normalization 成功，
  失敗未進入 Pydantic validation；NVIDIA 未呼叫，也沒有執行 dual UAT。
- `analysis_option_detail` 的 application logical budget 已由 1024 提高至 2048，作為
  provider-neutral、stage-specific 的 bounded headroom；目前只有 offline validation，
  尚待新的本機 qualification，當時尚待 dual-endpoint closeout。
- Live harness 的 analysis／report 失敗摘要現在只顯示安全 error code、operation、retryable
  與最後 recorder 的 operation/schema/mode/call count，不再依賴或暴露 `response.text`。
- Report-only diagnosis 確認四個 report provider calls 均為 HTTP 200、JSON Schema
  success、`finish_reason=stop`，但兩輪 application semantic validation 均以
  `provider_output_invalid` 失敗並觸發 deterministic degradation fallback；根因是
  provider narration schema 允許數字而 application safeguard 會拒絕部分數字。
- 本輪將 `ProviderReportSectionDraft.content` 收緊為不含 ASCII digits `0-9` 的
  provider-owned narration；persisted `ReportSectionDraft` 保留歷史讀取相容性，
  `fact_refs` 仍要求合法 `Fxxx` tokens，且 `_validate_refs`
  的 fact、confirmed evidence、KPI 與 numeric safeguards 保持不變。僅完成 offline
  validation，沒有新的 live provider、complete-local 或 dual-endpoint artifact；
  當時尚待 dual-endpoint closeout。
- 獨立 diff review 發現上述收緊若直接套用於 persisted `ReportSectionDraft`，會造成
  既有合法報告 reload 的 backward-compatibility regression。本輪已分離
  `ProviderReportSectionDraft`（strict digit-free provider DTO）與 persisted
  `ReportSectionDraft`（`NonEmptyStr`，保留歷史讀取相容性）；`PlanningReportPartA/B`
  使用前者，`PlanningReportDraft`／`PersistedPlanningReport` 使用後者。此修正保留
  `_validate_refs` defense-in-depth，並以 offline persistence／restart regression tests
  驗證；當時尚待 dual-endpoint closeout。

## PR #24 closeout

P6.7 將同一份持久化 `ReportSynthesis` 提供給 Results UI 與 Markdown renderer，並完成以下產品基線：

- article-style recommendation narrative；
- reviewed solution／case catalog 作為正式內容來源；
- deterministic solution–case–project consistency；
- Results refresh、history re-entry 與 Markdown download 重用已保存結果；
- reload、history 與 download 不重新呼叫 provider；
- secrets、raw provider responses 與內部識別資訊不進入正式報告。

PR #24 合併後，P6.7 不再是 feature-branch 狀態。

## Current architecture decisions

- LLM 只負責模糊需求理解、結構化訪談與敘事。
- matching、recommendation category、scoring、hard gates 與正式一致性由 deterministic code 負責。
- 每個專案綁定自己的 model profile。
- 所有真實模型呼叫共用單一 OpenAI-compatible adapter。
- NVIDIA OpenAI-compatible provider 是目前真實驗證基線。
- fake provider 僅用於 deterministic automated tests；禁止 silent runtime fallback。
- 正式 decision authority 與 processing boundary 由 confirmed facts 的
  deterministic policy 決定；provider 值不得改變持久化正式結果或 hard-gate input。
- P7.2 不修改 deterministic matching、scoring、hard gates、report synthesis 或 reviewed-case catalog。

## P7.2 checkpoints

### P7.2a — Representative dual-endpoint validation

目標是在不改變 deterministic decision logic 的前提下，明確 provider capability policy，並以一個代表情境驗證：

- NVIDIA OpenAI-compatible endpoint；
- 使用者自行啟動的一個本機 llama.cpp endpoint；
- readiness、discovery、analysis、report 四條 structured-output 路徑；
- authentication、token parameter 與 structured-output capabilities；
- 有限次 JSON Schema → JSON Object fallback；
- fallback 後的嚴格 Pydantic validation；
- 安全且可行動的 provider 錯誤。

P7.2a 通過只代表代表情境與雙端點基礎相容性成立，不得宣告完整 P7.2 完成。

### P7.2b — Full golden-scenario matrix

P7.2b 在 P7.2a 通過後：

- 擴展至四個 golden scenarios；
- 完成 NVIDIA／llama.cpp 雙端點 compatibility matrix；
- 驗證 deterministic results provider-independent；
- 完成產品與技術驗收後，才可宣告 P7.2 完成。

## P7.2 scope boundaries

包含：

- provider capability contract；
- authentication capability；
- token／reasoning parameter strategy；
- structured-output policy 與有限 fallback；
- 嚴格 schema validation；
- 安全錯誤；
- compatibility matrix；
- reload／history／download 不重新呼叫 provider。

不包含：

- 自動安裝或下載模型；
- Ollama、LM Studio、vLLM 專用 adapter；
- Docker；
- 雲端部署或帳號建立；
- 多 provider business logic；
- deterministic matching、scoring 或 hard-gate 修改；
- `report_synthesis.py` 重構；
- reviewed-case catalog 擴充。

## Next action

Start P8.1b-2 product-owner and release acceptance after the P8.1b-1 UI wording closeout. P7.2a has passed; P7.2b remains pending and the overall P7.2 initiative remains incomplete.

## Deferred

- Consumer installer 與 release packaging。
- 自動安裝 llama.cpp 或模型。
- 多 Agent、LangGraph、FAISS、Docker、雲端部署、帳號、online search 與 multi-tenancy。
- Production-grade credential encryption 與 PDF／DOCX export。
