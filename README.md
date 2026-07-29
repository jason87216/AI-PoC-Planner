# AI PoC Planner

AI PoC Planner 是一個本機優先、連接真實 OpenAI-compatible provider 的企業 AI 導入需求分析與 PoC 規劃工具。它把模糊的企業需求整理成可確認的事實、可比較的方案、受治理約束的建議，以及可下載的 Markdown 規劃報告。

## 目前產品狀態

目前 `main` 已包含可操作的 FastAPI 與 Streamlit 產品流程，而不是規格草稿或 scripted demo。

- 每個專案綁定自己的 model profile，正式分析只能使用該專案已選定、啟用並完成 readiness 驗證的 profile。
- 所有真實模型呼叫共用一個 OpenAI-compatible provider adapter；目前 NVIDIA OpenAI-compatible provider 是真實驗證基線。
- Discovery 已支援需求理解、修正、確認與最多三輪的針對性訪談。
- Assessment 已包含 deterministic opportunity matching、六維評分、recommendation category 與 hard gates。
- Results 已整合 reviewed-case matching、專案差距、可移植做法、分階段路線與 article-style report。
- SQLite 會保存 project、discovery、PlanningRun、assessment 與 report；完成後可從 history re-entry 回到 Results。
- Markdown 下載直接使用已保存報告；reload、history 與 download 不會重新呼叫 provider。
- P7.1 本機 UAT runtime 已完成，可用受監督的一鍵流程啟動與停止 FastAPI、Streamlit。
- fake provider 僅用於 deterministic automated tests，不是公開產品模式，也不存在 silent runtime fallback。

下一階段是 **P7.2 provider compatibility and structured-output policy**。P7.2 尚未開始實作；它將驗證同一個 adapter 對 NVIDIA 基線與使用者自行啟動的本機 llama.cpp 端點的一致支援。

## 產品流程

```text
建立專案並綁定 model profile
→ 輸入最小需求
→ AI 理解、使用者修正與確認
→ 最多三輪針對性訪談
→ confirmed facts
→ reviewed-case matching 與方案分析
→ deterministic scoring、recommendation category、hard gates
→ article-style Results 與持久化 Markdown report
→ history re-entry／download
```

## 決策邊界

LLM 只負責：

- 理解模糊需求；
- 提出結構化訪談問題；
- 產生受 schema 約束的候選方案與敘事內容。

程式碼負責：

- opportunity 與 reviewed-case matching；
- recommendation category；
- 六維評分與加權總分；
- hard gates；
- 正式建議、案例、分數與報告的一致性。

Provider 輸出不能覆寫 deterministic decision logic，也不能自行宣告正式 recommendation、score 或 gate disposition。

## Provider 與 model profile

每個專案保存自己的安全 model-profile snapshot。正式流程要求 profile 與目前已測試的真實連線一致；缺少、停用、未測試或不一致時會 fail closed，而不是改用 fake provider 或其他模型。

目前只有一個 OpenAI-compatible adapter。它是 NVIDIA 雲端基線與未來 llama.cpp 相容性驗證的共同邊界，不代表產品具有多 provider business logic 或多套專用 adapter。

## 持久化與安全

- SQLite 保存專案、版本、可見對話、confirmed facts、PlanningRun、assessment 與 report。
- 完成版本維持不可變；後續修改建立新的版本。
- 不保存 system prompt、chain of thought、LangChain tool trajectory、raw provider response、Authorization header 或 API key。
- 錯誤回應不得洩漏 secrets、raw response、內部路徑或技術診斷。
- 高影響人事、醫療、法律、信用或財務情境保持 assistive-only，人工保留最終決定。

## 本機執行

P7.1 提供專案自有的 Windows 本機 runtime，使用安全埠範圍：

- Streamlit UI：`18501-18599`
- FastAPI：`18610-18699`
- 不使用 `8000` 作為產品預設埠

從專案目錄啟動 UAT：

```powershell
.\scripts\start-local.ps1 -Mode Uat
```

查詢狀態與停止：

```powershell
.\scripts\status-local.ps1 -Mode Uat
.\scripts\stop-local.ps1 -Mode Uat
```

Runtime 只負責驗證專案 `.venv`、選擇安全埠、啟動／監督 FastAPI 與 Streamlit、開啟瀏覽器及可靠停止。它不會安裝 provider、下載模型或建立雲端帳號。

## 驗證基線

PR #24 已合併至 `main`，完成 P6.7 Results narrative、reviewed-case catalog consistency 與 report persistence 的產品驗收基線。NVIDIA OpenAI-compatible provider 已完成真實 Discovery、Assessment、Report 與 browser UAT；fake provider 仍只支援離線且可重現的自動測試。

## 明確不包含

目前不包含：

- 多 Agent 或 LangGraph；
- FAISS 或向量資料庫；
- Docker；
- 自動安裝 llama.cpp、Ollama、LM Studio、vLLM 或模型檔；
- provider 專用 adapter 或多 provider business logic；
- 雲端部署、帳號建立、多租戶；
- PDF／DOCX 匯出。

## 開發驗證

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

真實 provider UAT 必須明確 opt-in，且不得成為預設 CI 的秘密資料依賴。

## 文件

- [產品規格](docs/spec/SPEC.md)
- [實施計畫](docs/spec/PLAN.md)
- [任務拆分](docs/spec/TASKS.md)
- [專案記錄](PROJECT_LOG.md)

## License

MIT License. See [LICENSE](LICENSE).
