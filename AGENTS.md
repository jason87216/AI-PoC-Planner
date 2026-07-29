# Project Agent Rules

## Scope

- AI PoC Planner 是獨立 repository；只在明確授權的專案範圍內工作。
- 不讀取或修改 `.agents/`、`.claude/`、`tests/ai-poc-plan-45c6be62-e0e1-4878-95e6-8a984417891c.md`、Compliance Approval Agent 或其他專案。
- 行為或資料契約改變時先同步 `docs/spec/`；狀態改變時同步 `PROJECT_LOG.md` 與 `docs/spec/TASKS.md`。

## Decision Boundaries

- LLM 只負責模糊需求理解、結構化訪談與受 schema 約束的敘事。
- matching、recommendation category、scoring、hard gates 與正式結果一致性必須由 deterministic code 負責。
- Provider 輸出不得直接決定正式 recommendation、權重、總分、gate disposition 或 catalog 事實。
- 每個專案綁定自己的 model profile；正式流程必須使用該專案已選定、啟用並測試通過的 profile。

## Provider Rules

- 所有真實模型呼叫使用同一個 OpenAI-compatible provider adapter。
- 禁止 silent provider、model 或 fake-provider fallback。
- fake provider 只用於 deterministic automated tests，不是產品 runtime。
- 真實 provider UAT 必須明確 opt-in，不得成為預設 CI 前提。
- 不新增 provider 專用 business logic，除非規格明確授權。

## Security Rules

- 不顯示、記錄、提交或落庫 secrets、API keys、tokens、passwords、cookies 或 Authorization headers。
- 不將 raw provider response、system prompt、chain of thought、reasoning trace 或 tool trajectory 寫入資料庫或錯誤回應。
- Provider 錯誤必須安全、可行動，且不得洩漏內部路徑、SQLite 位置或敏感診斷。
- Streamlit session state 不是可信或唯一的持久化來源；產品資料經 FastAPI 與 SQLite 邊界存取。

## Runtime Rules

- Streamlit UI 使用 `18501-18599`。
- FastAPI 使用 `18610-18699`。
- 不使用 `8000` 作為產品預設埠。
- Runtime 不安裝、下載或管理模型與 provider。

## Architecture Constraints

- 不新增 LangGraph、多 Agent、FAISS、Docker、雲端帳號、雲端部署或模型自動安裝。
- 不修改 deterministic matching、scoring、hard gates、provider profile、report synthesis 或 reviewed-case catalog，除非當前任務明確授權。
- 不把 business rules 藏進 prompt；Pydantic contracts 與程式驗證保持正式邊界。

## Git Rules

- 修改前後檢查狀態與 diff，只 stage 明確授權的檔案。
- 不使用 `git add .` 作為預設行為。
- 未獲明確授權不得 commit、push、建立 PR、改 remote 或重寫歷史。
- commit 前檢查 staged diff、秘密資料與本機 artifacts。
