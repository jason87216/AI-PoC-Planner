# AI PoC Planner

AI PoC Planner 是一個本機優先、連接真實 OpenAI-compatible provider 的企業 AI 導入需求分析與 PoC 規劃工具。它把模糊的企業需求整理成可確認的事實、可比較的方案、受治理約束的建議，以及可下載的 Markdown 規劃報告。

## 目前產品狀態

目前 `main` 已包含可操作的 FastAPI 與 Streamlit 產品流程，而不是規格草稿或 scripted demo。

- 每個專案綁定自己的 model profile，正式分析只能使用該專案已選定、啟用並完成 readiness 驗證的 profile。
- 所有真實模型呼叫共用一個 OpenAI-compatible provider adapter；P7.2a 已以 NVIDIA 與本機 llama.cpp 代表端點完成相容性 checkpoint。
- Discovery 已支援需求理解、修正、確認與最多三輪的針對性訪談。
- Assessment 已包含 deterministic opportunity matching、六維評分、recommendation category 與 hard gates。
- Results 已整合 reviewed-case matching、專案差距、可移植做法、分階段路線與 article-style report。
- SQLite 會保存 project、discovery、PlanningRun、assessment 與 report；完成後可從 history re-entry 回到 Results。
- Markdown 下載直接使用已保存報告；reload、history 與 download 不會重新呼叫 provider。
- P7.1 本機 UAT runtime 已完成，可用受監督的一鍵流程啟動與停止 FastAPI、Streamlit。
- fake provider 僅用於 deterministic automated tests，不是公開產品模式，也不存在 silent runtime fallback。

目前狀態：

- **P7.2a Representative dual-endpoint compatibility：Complete**
- **P7.2b Full golden-scenario compatibility matrix：Pending**
- **P7.2 overall：Incomplete**；四個 golden scenarios 的完整雙端點矩陣尚未宣告完成。
- **P8.1a Portfolio baseline：Complete**
- **P8.1b Product-owner and release acceptance：Pending**

P7.2a 的完成只代表 `governed_access` 代表情境通過雙端點驗證，不代表所有情境或所有模型／runtime 都已認證。

## 這個工具適合誰？

- 企業業務負責人：把模糊的 AI 導入構想整理成可討論、可審查的 PoC 方案。
- PoC／轉型負責人：透過 bounded Discovery、confirmed facts 與方案比較，準備下一步決策。
- 技術面試官與工程團隊：檢視真實 provider 整合、結構化輸出、持久化與 deterministic governance 邊界。
- 作品集讀者：用一個可啟動的本機產品流程理解 AI 與程式規則如何協作。

AI 的價值在於理解模糊需求、提出有脈絡的訪談問題，以及產生受 schema 約束的候選敘事；正式推薦、分數、hard gates、權限邊界與案例事實仍由程式驗證與決定。

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

目前只有一個 OpenAI-compatible adapter。它是 NVIDIA 雲端基線與本機 llama.cpp 代表端點的共同邊界，不代表產品具有多 provider business logic 或多套專用 adapter。

Profile 目前由「模型設定」頁面建立、編輯、測試與選擇；產品沒有 profile import／export UI。private local `model_profiles.json` 是 runtime state，不是應提交或放入作品集的範例檔。

### Provider capability contract

每個 profile 必須明確宣告 transport capability，不以 provider 或 model 名稱猜測：

| Capability | Supported values |
| --- | --- |
| Transport | OpenAI-compatible `/v1/chat/completions` |
| Authentication | `none`、`bearer_optional`、`bearer_required` |
| Token parameter | `max_tokens`、`max_completion_tokens` |
| Reasoning parameter | `unsupported`、`reasoning_effort` |
| Structured output | `json_schema`、`json_object` |

只會依 profile capability 使用 `Authorization: Bearer <token>`；不支援 `x-api-key`、query-string key、Basic、OAuth exchange、AWS-style signing 或其他非本產品 contract 的 authentication。這是明確的 compatibility scope，不是「支援所有 OpenAI-compatible endpoint」的宣稱。

作品集可用兩種非敏感代表設定說明範圍：remote Bearer endpoint 使用文件用 `example.invalid` base URL 與 `bearer_required`；local no-auth endpoint 使用 `http://127.0.0.1:8080/v1` 與 `none`。兩者都必須由使用者明確選擇 model name 與其他 capability，文件不放 real key。

## 持久化與安全

- SQLite 保存專案、版本、可見對話、confirmed facts、PlanningRun、assessment 與 report。
- 完成版本維持不可變；後續修改建立新的版本。
- 不保存 system prompt、chain of thought、LangChain tool trajectory、raw provider response、Authorization header 或 API key 到 project SQLite、public API、logs、UI 或 Markdown report。
- MVP 仍會將 API key 以明文保存於本機 private `model_profiles.json`，以支援已選 profile 的 provider 呼叫；這不是 production-grade credential storage，也不等同於加密保存。若要部署到真實企業環境，後續應改用 Windows Credential Manager、OS keychain 或其他受控 secret store。
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

第一次啟動：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\start-local.ps1 -Mode Uat
```

啟動後依序操作：

1. 在「模型設定」建立一個 OpenAI-compatible model profile；目前 UI 不提供 profile import。
2. 填入 endpoint、模型名稱與 capability；API key 只保存在本機 profile，不會顯示在公開回應或報告。
3. 執行 readiness test；未測試通過的 profile 不可進入正式分析。
4. 建立專案，使用下方的 synthetic `governed_access` Demo 完成需求理解、訪談、Assessment 與 Results。
5. 從「專案歷史」重新進入結果，或下載已持久化的 Markdown report。

沒有可用且已測試的 provider 時，產品會 fail closed；不會偷偷切換 fake provider。Runtime 也不會啟動 llama.cpp、安裝 provider、下載模型或建立雲端帳號。

## `governed_access` portfolio Demo

Demo 直接重用 [`tests/fixtures/product_acceptance/scenarios.json`](tests/fixtures/product_acceptance/scenarios.json) 的 `scenario_id=governed_access`。這是作品集用的 synthetic fixture，不是真實公司的員工或權限資料。

展示路徑：

`模型設定 → readiness test → 新建專案 → 需求理解與修正 → 確認 → bounded interview → Assessment → Results → Markdown download → 專案歷史／reload`

展示重點是：主管保留最終核准、AI 不直接寫入權限、未核准的外部個資不送出，以及 deterministic recommendation、reviewed cases 與 hard gates 不會被 provider 內容覆寫。

不要在作品集截圖或報告中放入 API key、Authorization、provider raw response、prompt、reasoning、事實 token、SQLite 路徑或暫存 evidence 路徑。

## 驗證基線

PR #24 已合併至 `main`，完成 P6.7 Results narrative、reviewed-case catalog consistency 與 report persistence 的產品驗收基線。PR #26 已完成 P7.2a `governed_access` 雙端點 compatibility checkpoint；P7.2b 四情境矩陣仍待後續驗證。NVIDIA OpenAI-compatible provider 已完成真實 Discovery、Assessment、Report 與 browser UAT；fake provider 仍只支援離線且可重現的自動測試。

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
- [P8.1 portfolio baseline](docs/portfolio/P8_1_PORTFOLIO_BASELINE.md)

## License

MIT License. See [LICENSE](LICENSE).
