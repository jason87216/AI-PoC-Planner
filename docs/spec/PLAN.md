# Viable MVP implementation plan

## Status

AI PoC Planner 已完成從 real-provider foundation、durable project history、Discovery、Assessment、reviewed-case matching、article-style Results，到 P7.1 本機 UAT runtime 的主要產品流程。

目前 P7.2a representative dual-endpoint compatibility 已完成；P7.2b full golden-scenario matrix 仍待驗證。P8.1a portfolio baseline 可在不宣告完整 P7.2 的前提下進行。

## Guiding decisions

- 正式分析必須使用專案綁定、已啟用且測試通過的真實 model profile。
- 所有真實模型呼叫共用單一 OpenAI-compatible provider adapter。
- fake provider 是 deterministic automated-test double，不是產品模式。
- 禁止 silent provider、model 或 fake-provider fallback。
- LLM 負責模糊需求理解與敘事；matching、recommendation category、scoring、hard gates 與正式一致性由 deterministic code 負責。
- 每個 phase 以小型、可審查 PR 完成；技術測試通過不自動等於產品 checkpoint 通過。

## Phase status

| Phase | Status | Current baseline |
| --- | --- | --- |
| Phase 0 | Complete | viable-MVP 規格與 real-provider-first 邊界 |
| Phase 1 | Complete | project-bound model profiles 與單一 OpenAI-compatible adapter |
| Phase 2 | Complete | project/version、visible conversation、confirmed facts 與 SQLite persistence |
| Phase 3 | Complete | requirement understanding、correction、confirmation 與 bounded Discovery |
| Phase 4 | Complete | structured options、六維評分、recommendation category 與 hard gates |
| Phase 5 | Complete | reviewed cases、PlanningRun 與 persisted Markdown report |
| Phase 6 | Complete | FastAPI／Streamlit 產品流程、history re-entry、Results 與 download |
| P7.1 | Complete | 本機啟動／狀態／停止與 UAT runtime |
| P7.2 | In progress | P7.2a Complete；P7.2b Pending；overall incomplete |
| Phase 8 | In progress | P8.1a Complete；P8.1b-1 Complete；P8.1b-2 release acceptance Pending |

## Phase 7 — Local runtime and provider compatibility

### P7.1 — Local UAT runtime — Complete

P7.1 已完成：

- 專案自有 `.venv` 與 runtime identity 驗證；
- FastAPI／Streamlit 的啟動、監督、狀態與停止；
- UI 使用 `18501-18599`；
- API 使用 `18610-18699`；
- 不使用 `8000` 作為產品預設埠；
- Local／Uat state isolation；
- browser launch 與 safe logs。

P7.1 只負責本機 runtime，不負責安裝 provider、下載模型、建立雲端帳號或發佈 consumer installer。

### P7.2 — Provider compatibility and structured-output policy — In progress

#### Formal goal

以同一個 OpenAI-compatible adapter，一致支援：

- NVIDIA OpenAI-compatible 雲端驗證基線；
- 使用者自行啟動的本機 llama.cpp OpenAI-compatible endpoint。

P7.2 不建立第二套 provider adapter，也不加入多 provider business logic。

#### In scope

- provider capability policy；
- model-profile capability contract；
- authentication capability；
- token parameter capability；
- reasoning parameter capability；
- structured-output capability；
- readiness、discovery、analysis、report 四條 structured-output 路徑的一致策略；
- 有限次 JSON Schema → JSON Object fallback；
- fallback 後仍執行嚴格 Pydantic validation；
- 安全且可行動的 provider errors；
- NVIDIA／llama.cpp compatibility matrix；
- reload、history、download 重用 persisted state，不重新呼叫 provider；
- deterministic results 在不同 endpoint 間保持 provider-independent。

#### Structured-output policy

1. Model profile 明確宣告 endpoint 支援的 authentication、token、reasoning 與 structured-output capabilities。
2. Adapter 依 capability contract 產生單一、可預測的 request shape，不以隱性重試猜測 provider 行為。
3. 優先使用 JSON Schema structured output。
4. 只有在已定義且可辨識的 capability failure 時，允許有限次降級至 JSON Object。
5. JSON Object 回應仍必須通過相同的嚴格 Pydantic validation；validation failure 不得被容錯為成功。
6. 不允許改用其他 provider、其他 model、fake provider 或未綁定 profile。
7. 所有錯誤必須可行動，且不得包含 secrets、Authorization header 或 raw provider response。

#### Out of scope

- 自動安裝或下載模型；
- Ollama、LM Studio、vLLM 專用 adapter；
- Docker；
- 雲端部署與帳號建立；
- 多 provider business logic；
- 修改 deterministic matching、recommendation category、scoring 或 hard gates；
- 重構 `report_synthesis.py`；
- 擴充 reviewed-case catalog；
- consumer installer 或 release packaging。

### P7.2a — Representative dual-endpoint validation

P7.2a 使用一個代表情境，對 NVIDIA 與一個本機 llama.cpp endpoint 驗證：

- readiness；
- discovery；
- analysis；
- report；
- authentication／optional local token；
- token／reasoning parameter policy；
- JSON Schema → JSON Object bounded fallback；
- strict Pydantic validation；
- safe actionable errors；
- reload／history／download 不重新呼叫 provider。

P7.2a 的 checkpoint 是「一個代表情境的雙端點路徑成立」。P7.2a 通過不得寫成完整 P7.2 已完成。

### P7.2b — Full golden-scenario compatibility matrix

P7.2b 在 P7.2a 通過後：

- 擴展至四個 golden scenarios；
- 對 NVIDIA 與 llama.cpp 完成完整 compatibility matrix；
- 比較 readiness、discovery、analysis、report 的成功與失敗行為；
- 驗證 matching、recommendation category、scores、hard gates 與 persisted formal results provider-independent；
- 完成產品與技術驗收。

只有 P7.2b matrix 與驗收完成後，才可宣告 P7.2 Complete。

## Phase 8 — Portfolio and release UAT

P8.1a portfolio baseline 可基於已完成的 P7.2a 代表情境證據先行整理；這不會改變 P7.2b Pending 或 P7.2 overall incomplete 狀態。

### P8.1a — Portfolio baseline — Complete

- 同步 README、PROJECT_LOG 與本計畫中的產品狀態；
- 提供五分鐘啟動、model profile readiness 與 synthetic `governed_access` Demo runbook；
- 建立架構／workflow 圖、截圖清單、P7.2a 脫敏 evidence 摘要與 limitations；
- 不修改 application behavior、provider implementation、deterministic logic、database schema 或 dependencies；以上文件基線已完成。

### P8.1b-1 — Traditional Chinese UI wording and product guidance — Complete

- 以繁體中文整理模型設定、能力選擇、模型可用性測試、需求訪談、評估、報告與歷史頁面的產品文案；
- 對無可用模型、連線失敗與可重試錯誤提供 fail-closed、可行動的使用者引導；
- 明確說明 AI 協助理解與整理，正式推薦、分數與硬性限制由程式規則負責；
- UI 顯示安全能力標籤與端點文件提示，不根據品牌或模型名稱猜測能力；
- 未修改 API 契約、provider、deterministic logic、SQLite schema、依賴或 runtime；本輪只完成 offline validation。

### P8.1b-2 — Product-owner and release acceptance — Pending

- 審查繁體中文文案與 business usefulness；
- 驗證 blocked-no-provider、Discovery、Assessment、Results、history re-entry 與 download；
- 完成 release-readiness acceptance，再決定是否啟動 P7.2b。
- 人工驗收已揭露 runtime database preflight 與 model settings information architecture blocking defects；本修正以 bounded application/UI changes 修復，並重新建立乾淨 UAT schema v8。
- 本修正不改變 provider、deterministic assessment、scoring、hard gates 或正式結果邏輯；P8.1b-2 必須重新人工驗收後才能改變狀態。

P8.1b overall remains Pending until P8.1b-2 acceptance is complete.

## Testing policy

| Layer | Purpose |
| --- | --- |
| Unit／contract | Pydantic schemas、capability policy、fact references、scores、gates |
| Repository／service | profiles、projects、versions、PlanningRun、reports 與 immutable transitions |
| API | readiness、Discovery、Assessment、Report 與 safe errors |
| Fake-provider | deterministic automated behavior only |
| Opt-in integration | NVIDIA 與使用者自行啟動的 llama.cpp endpoint |
| UI／UAT | FastAPI-bound Streamlit flow、reload、history、download 與 browser behavior |

真實 provider UAT 必須明確 opt-in，不得要求 CI 保存 secrets 或自動安裝模型。

## Definition of done

P7.2 只有在以下條件全部成立時才完成：

- 單一 OpenAI-compatible adapter 通過 NVIDIA／llama.cpp 雙端點矩陣；
- 四個 golden scenarios 完成 readiness、discovery、analysis、report 驗證；
- bounded fallback 與 strict validation 行為一致；
- deterministic results provider-independent；
- reload、history、download 不重新呼叫 provider；
- errors 安全且可行動；
- 產品與技術 checkpoint 均通過。
