# AI PoC Planner Interview Notes

這份文件是面試準備材料，不是產品規格或內部開發流水帳。回答以 AI software engineer、Agent／AI workflow、Solution Engineer 與企業 AI 導入職缺的面試情境為目標。

## 30 秒版本

AI PoC Planner 是一個本機優先的企業 AI 導入需求分析與 PoC 規劃工具。它用 LLM 理解模糊需求、提出有界訪談問題並整理候選敘事，再由 deterministic code 完成 matching、六維評分、hard gates 與正式推薦。canonical synthetic demo 是企業權限申請與風險審查，成果可以持久化、從 History 重新開啟並下載 Markdown report。核心設計是讓 AI 協助理解，但不讓 AI 直接批准權限或決定正式分數。

## 90 秒版本

我做這個專案是因為企業常有模糊的 AI 構想，卻沒有一個可以確認需求、比較方案和說明風險的流程。產品從最小 brief 開始，經過 AI requirement understanding、使用者確認與最多三輪 bounded interview，形成 confirmed facts。接著 application service 使用 reviewed catalog 與 deterministic policy 產生方案、六維評分、hard gates、decision authority 與 processing boundary；LLM 只提供受 schema 約束的候選內容。

技術上使用 Streamlit 作為 UI、FastAPI 作為 API 邊界、LangChain 與 OpenAI-compatible adapter 整合 structured output，並用 Pydantic 驗證 DTO。SQLite 保存 project、immutable version、可見對話、facts、analysis 與 report，因此 Results、History 和 Markdown download 都能重用同一份正式結果。遇到 provider 輸出無效、fact reference 不存在或 semantic validation 失敗時，流程在 persistence 前 fail closed，只允許 bounded repair，不用 fallback 偽造結果。

## 為什麼做這個專案

我想把「AI 應該幫忙什麼」和「AI 不應該決定什麼」放進同一個可操作產品。對企業導入來說，能否說明 evidence、責任、風險與下一步，通常比單次模型回答更重要。這個專案也讓我可以實際處理 provider capability、structured output、持久化、Windows runtime 與安全錯誤，而不只展示一個聊天介面。

## 架構如何運作

Streamlit 只呼叫 FastAPI；application service 再協調 structured-output executor、provider adapter、deterministic policy 與 SQLite repository。模型輸出先通過 JSON／Pydantic 與 application semantic validation，正式 recommendation、scores、gates、case matching 與 persistence 則由程式完成。完成版本 immutable，History re-entry 讀取已保存的 analysis 與 report，所以不會重新產生模型費用。

## 為什麼不讓 LLM 決定分數與推薦

分數、推薦與 hard gates 是正式決策資料，不應隨著模型溫度、措辭或 provider 差異漂移。LLM 可以提出敘事、假設與候選方案，但正式結果要能由 confirmed facts、catalog 與固定規則重現。這樣測試可以直接驗證 safety boundary，也能在 report reload 時保持一致。對權限申請這類情境，人員仍是最終核准者，AI 只提供 assistive 建議。

## 最困難的工程問題

最難的是讓 provider 的 structured output 通過 schema，還要符合 application 的語義與 deterministic catalog。形式上合法的 JSON 仍可能引用不存在的 fact、使用不相容的 solution category，或與 hard gates 矛盾。我的做法是在 provider DTO、semantic validation、deterministic assessment 與 persistence transaction 之間建立明確邊界；失敗就安全停止，不保存 partial report，也不把錯誤內容原樣顯示給使用者。

另一個實際難題是 Windows runtime 與資料目錄權限。啟動器需要監督 FastAPI 和 Streamlit，但不能把 provider、模型或資料庫管理混在一起；因此 runtime 使用既有的 state、port 與 stop lifecycle，錯誤則以安全訊息呈現。

## 如何處理 Provider 不穩定

先使用專案綁定、啟用且 readiness test 通過的 profile，禁止 silent fallback 到其他模型或 fake provider。Structured output 只允許既定的有限降級與 bounded semantic repair，最多兩次嘗試；仍無法驗證就回傳 stable safe error。provider raw response、prompt、Authorization 與 endpoint 不進 UI、SQLite、logs 或 Markdown。

這種策略的重點不是把成功率無限拉高，而是讓失敗可理解、可重試且不污染正式結果。真正需要改變 timeout、schema 或 provider capability 時，應該另開 bounded engineering change，而不是在作品集流程中偷偷放寬規則。

## 如何設計持久化與 History Re-entry

project、version、visible conversation、confirmed facts、analysis 與 report 都保存於 SQLite。完成版本 immutable；修改時建立新的 version，避免在歷史結果上原地覆寫。Results、History 與 Markdown renderer 都讀取 persisted state，因此重新進入或下載不需要再次呼叫 provider。

我會把「沒有重新呼叫 provider」當成產品行為與測試條件，而不是只看畫面是否相同。這同時控制成本，也讓面試官能清楚看到 reload 的一致性邊界。

## 安全與治理邊界

API key 仍是本機 private model profile 的 MVP 儲存方式，並不是加密的 production credential store。產品不把 key、Authorization header、raw provider response、prompt、reasoning、UUID、SQLite path 或內部 endpoint 放入正式 UI、public API、SQLite report 或作品集圖片。權限申請流程保留 human final decision，AI 不直接批准、不直接修改正式權限，敏感資料只能在核准的 private boundary 處理。

## 測試策略

離線測試使用 fake provider 作為 deterministic test double，驗證 DTO、semantic validation、persistence、API、UI 與 no-partial-persistence 行為；fake provider 不是產品 runtime。真實 provider UAT 是明確 opt-in，另外驗證 readiness、Discovery、Assessment、Report、History 與 download。已驗證基線為 889 passed、7 個 live-provider tests 預設 skipped、CI passed；不能把六張作品集圖片說成 automated test。

## 技術取捨

我選擇 SQLite 而不是外部資料庫，因為 MVP 是 local-first、single-user，且需要讓完整 version 可以簡單保存與重新載入。選擇單一 service flow 而不是 LangGraph 或多 Agent，是因為目前主要問題是責任邊界與可驗證 state transition，不是 agent delegation。reviewed cases 使用受審核 catalog，而不是即時搜尋，換取來源與適用範圍的可控性。

## 已知限制

P7.2b 四個 golden scenarios 的完整雙端點 compatibility matrix 尚未完成，P7.2 overall 仍是 incomplete。Consumer installer、cloud deployment、multi-tenancy、PDF／DOCX export 與 production-grade credential store 都是 deferred。MVP 的 local profile 仍需使用者自行設定並通過 readiness，產品不會自動下載模型或安裝 provider。

## 常見面試問題

### 為什麼使用 LangChain？

LangChain 在這裡是模型呼叫與 structured output 的整合工具，不是 business-rule engine。它幫助我把 provider transport、schema、Pydantic validation 與 bounded retry 放在可測試的 executor 邊界。正式 matching、scoring、hard gates 與 persistence 仍由 application code 負責，因此不依賴 LangChain 的隱含 agent 行為。

### 為什麼不用 LangGraph／多 Agent？

目前產品需要的是清楚、可重播的 service workflow，不是多角色之間的開放式協商。增加多 Agent 會引入更多 state、retry、observability 與責任歸屬成本，卻沒有改善這個 PoC 的核心治理問題。若未來有真正需要長流程協作的場景，我會先定義可持久化的 state machine 與 ownership，再評估是否引入 orchestration framework。

### 如何避免 LLM 幻覺影響正式決策？

首先把模型輸出限制在 typed structured output，並在 application 邊界做語義驗證。其次，正式 recommendation、分數、gates、decision authority 與 processing boundary 只從 confirmed facts、reviewed catalog 與 deterministic policy 產生。最後，任何引用不存在 fact 或不符合一致性規則的輸出都 fail closed，不會用 fallback 把模型文字包裝成正式結果。

### 為什麼使用 SQLite？

這個 MVP 是本機優先與單使用者流程，SQLite 足以提供 transaction、durable state 與簡單部署。更重要的是，它可以把 project、immutable version、conversation、facts、analysis 和 report 保存在同一個本機邊界。未來若要支援多租戶或集中式治理，我會重新評估資料庫、secret store、權限模型與 audit pipeline，而不是直接把 SQLite 當成企業最終方案。

### 如何保證重新開啟結果時不再次花費模型費用？

History 與 Results 使用 persisted analysis／report，而不是依 brief 重新計算。完成版本保存完整的正式結果並保持 immutable；Markdown download 也直接使用同一份 persisted synthesis。測試會檢查 re-entry、reload 與 download 的 provider call count，而不只檢查畫面文字。

### Provider 不支援 schema 時怎麼辦？

先由 model profile 明確宣告 structured-output capability，adapter 依 capability contract 選擇 JSON Schema 或既定的 JSON Object 路徑。JSON Object 仍必須通過同一套 Pydantic 與 semantic validation；不會因為 provider 不支援 schema 就把欄位全部放寬。若 bounded repair 後仍不合法，產品安全停止並提供可行動的錯誤。

### 如何保護 API key？

目前 key 只存在本機 ignored 的 private model profile，用於已選 profile 的 provider call；這是 MVP limitation，不是加密或 production-grade secret management。產品不把 key 放進 public API、SQLite report、logs、Markdown 或截圖。企業化下一步會使用 Windows Credential Manager、OS keychain 或其他受控 secret store，並重新設計 rotation 與 access audit。

### 如何測試真正的 provider？

離線測試使用 fake provider，只驗證 deterministic、API、persistence 與 UI 行為，不把 fake 結果當成真實模型驗收。真實 provider 測試是 opt-in，必須使用已啟用且 readiness 通過的 project-bound profile，並以一個受控 scenario 驗證 Discovery、Assessment、Report、reload 與 download。測試紀錄只保留安全摘要與 call count，不保存 raw response 或 secret。

### 這個專案如何擴充成企業產品？

我會先補齊 P7.2b compatibility matrix，再處理受控 secret store、集中式 audit、角色權限、租戶隔離與可觀測性。接著把 reviewed catalog、policy version 與 evidence provenance 做成可審核的治理資料，而不是讓模型自行更新。最後才評估雲端部署、背景工作、enterprise identity 與更大規模的資料庫。

### 你本人在這個專案負責什麼？

我負責把產品需求拆成可驗證的 workflow、provider contract、deterministic decision boundary 與持久化模型，並完成 FastAPI／Streamlit 整合、Windows runtime、UAT 與測試設計。遇到 provider 輸出與正式 catalog 不一致時，我把修正放在 DTO、semantic validation、safe error 與 transaction 邊界，而不是靠 prompt 期待模型自律。作品集展示的重點，是我能同時處理產品流程、工程可靠性與 AI 治理，而不只串接一次 API。

## 履歷 bullet

- 建立本機優先的 AI PoC Planner，串接 FastAPI、Streamlit、LangChain、Pydantic 與 SQLite，將模糊企業需求轉成可確認 facts、方案比較、六維評分、hard gates 與 Markdown report。
- 設計 LLM／deterministic responsibility boundary：模型負責理解與敘事，正式 matching、recommendation、scoring、治理限制與一致性由程式驗證，並以 immutable version 支援 History re-entry。
- 完成 OpenAI-compatible structured-output、bounded validation／repair、safe error mapping 與 Windows quickstart；離線基線 889 passed，真實 provider UAT 以 opt-in 方式驗證。
