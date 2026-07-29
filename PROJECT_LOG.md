# Project Log

## Current status

- PR #24 已合併至 `main`。
- Merge commit：`91bb6b45f9be2249d9cd9edfd11a309bd806f321`。
- P6.7 已完成。
- Results narrative、reviewed-case catalog consistency 與 report persistence 已通過產品驗收。
- P7.1 本機 UAT runtime 已完成並維持目前啟動／停止基線。
- Current goal：P7.2 provider compatibility and structured-output policy。
- P7.2 尚未開始實作；本次只同步文件狀態與開發約束。

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
- P7.2 不修改 deterministic decision logic、report synthesis 或 reviewed-case catalog。

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

建立 P7.2a implementation branch 前，先完成 capability contract 與代表情境驗收規格。P7.2 程式開發目前保持未開始狀態。

## Deferred

- Consumer installer 與 release packaging。
- 自動安裝 llama.cpp 或模型。
- 多 Agent、LangGraph、FAISS、Docker、雲端部署、帳號、online search 與 multi-tenancy。
- Production-grade credential encryption 與 PDF／DOCX export。
