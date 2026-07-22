# AI PoC Planner

AI PoC Planner 是一個規格中的公開 AI 工程作品：透過單一 LangChain Agent 進行結構化需求訪談，結合本機案例檢索、固定評分框架與風險 hard gates，產生可追蹤、可測試、可匯出的 AI 導入 PoC 建議。

> 專案狀態：**deterministic offline vertical slice、M2.2-lite SQLite planning-run
> persistence，以及最小 LangChain + FastAPI planning slice available**。所有既有
> demo 與測試皆不需要 API key 或網路。

## 核心價值

- 把模糊的企業需求轉成結構化問題、缺口與下一步。
- 將商業價值、資料成熟度、技術貼合度、架構可控性、治理準備度與使用者採納分開評估。
- 先套用風險與法規 hard gates，再解讀加權分數，避免高 ROI 抵銷不可接受風險。
- 以案例知識庫支撐建議，而不是只靠模型自由生成。
- 產生 Pydantic 驗證的 PoC proposal，並匯出 Markdown 報告。

## MVP 架構

- Python
- FastAPI
- Streamlit
- LangChain 單一 Agent
- Tool Calling
- Pydantic Structured Output
- SQLite：專案、訪談、conversation state、評估、報告與案例 metadata
- FAISS：案例 embeddings
- pytest + deterministic fake model
- Docker Compose
- OpenAI-compatible model adapter；核心流程不依賴單一供應商

PostgreSQL、pgvector、Qdrant、雲端向量資料庫、多 Agent、多租戶與雲端部署均不在 MVP 內。

## 規格入口

- [研究報告](deep-research-report.md)
- [產品與技術規格](docs/spec/SPEC.md)
- [實作計畫](docs/spec/PLAN.md)
- [可執行任務](docs/spec/TASKS.md)
- [專案狀態與交接](PROJECT_LOG.md)

## 本機開發

主要支援 Python 3.12。以下是 PowerShell 的標準 Python 流程，不要求 Poetry、
PDM 或 uv：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ai_poc_planner
python -m ai_poc_planner demo
python -m ai_poc_planner planning-demo
python -m pytest
python -m ruff check .
```

`python -m ai_poc_planner` 顯示簡短 usage。`demo` 執行固定且完全離線的流程，
預設將報告寫入 Git ignored 的 `artifacts/demo-report.md`：

```text
Project: 客服知識檢索 PoC
Weighted score: 100
Gate disposition: pass
Recommendation: 建議進行
Report: ...\artifacts\demo-report.md
```

可自訂輸出位置：

```powershell
python -m ai_poc_planner demo --output artifacts/my-demo.md
```

目前 offline demo 會建立固定分析專案、載入合成訪談資料、由 fake provider
產生 typed facts／六組 tool inputs、執行 deterministic services、呼叫
`assess_project(AssessmentInput)` 重算六維分數與 `HG-01`～`HG-07`，再產生
validated proposal 與固定章節 Markdown。Provider 無權指定正式分數、weighted
score、gate disposition 或 recommendation。

### LangChain + FastAPI planning slice

最小 API 提供 `GET /health` 與 `POST /v1/planning/interpret`。後者接受
`natural_language_request` 與可選的 `clarification_answers`，由一個
`langchain.agents.create_agent` Agent 抽取 `PlanningIntent`，再呼叫唯一的 typed
planning tool。該 tool 實際組合既有的 `match_opportunities()` 與
`assess_deployment_posture()`；HTTP response 只採用這個工具的 validated input／output。

API composition 必須由呼叫端注入 LangChain `BaseChatModel`；本專案尚未提供 live
provider runtime 或供直接啟動的 production server。`python -m ai_poc_planner
planning-demo` 與自動測試使用 LangChain 官方 `GenericFakeChatModel` 的 scripted tool
call trajectory。它展示 Agent orchestration 與 typed tool integration，**不代表實際模型
理解品質**。

此 slice 不建立或更新 `PlanningRun`，也不產生六維分數、recommendation、hard gate、
proposal 或 Markdown report。若資料不足，API 依既有 matching／deployment outputs 以
固定繁中模板回傳最多四題澄清問題；呼叫端需連同原始需求重新提交補答。

### Persisted planning flow

在明確注入 LangChain chat model、SQLite path 與 deterministic assessment provider 後，
FastAPI 另提供：`POST /v1/planning/runs`、`POST /v1/planning/runs/{run_id}/clarifications`
與 `GET /v1/planning/runs/{run_id}`。它會將 validated `PlanningIntent` 保存到既有
`PlanningRun`，以每批最多四題的方式保存澄清；正式資料齊備後，重用既有評估、hard
gate、proposal 與 Markdown pipeline，並將完整結果保存為 `completed`。
建立 run 時可同時提交可選的初始 JSON 業務事實；這些事實只保存為正式 workflow 可用的
已知資訊，不保存 Agent 軌跡或 deterministic 評估輸出。

reload 不會呼叫 LangChain：它只從 saved intent 重新執行 deterministic matching 與
deployment posture；assessment、proposal 與 Markdown 則直接讀取保存結果。資料庫不保存
Agent messages、prompt、tool trajectory、provider response 或完整 planning evaluation。
目前仍沒有 live provider runtime；測試使用明確注入的 scripted chat model 與既有 fake
assessment provider，僅展示 orchestration，不代表實際模型理解品質。

### Streamlit fake-mode 展示

先在一個 PowerShell 視窗啟動明確的本機 fake API；它只使用 Git ignored 的
`artifacts/streamlit-demo.sqlite3`：

```powershell
python -m uvicorn ai_poc_planner.app.demo_server:create_demo_app --factory --host 127.0.0.1 --port 8000
```

再在另一個視窗啟動單頁 Streamlit UI：

```powershell
python -m streamlit run src/ai_poc_planner/ui/streamlit_app.py
```

UI 只透過 HTTP 呼叫 `GET /health`、`POST /v1/planning/runs`、
`POST /v1/planning/runs/{run_id}/clarifications` 與 `GET /v1/planning/runs/{run_id}`；
它不讀寫 SQLite、不 import application service 或 LangChain，也不重算 matching、
deployment、assessment 或 hard gates。側邊欄可用 run ID 重載正式狀態；同一次瀏覽器
session 會以只讀時間軸顯示需求與提交過的回答，重載後則只顯示原始需求與累積業務資訊摘要。

這個 fake server 的 chat model 是無狀態 scripted demo：它只檢查補答是否已包含三個
固定展示部署欄位，並回傳固定 incomplete／ready intent；它**不分析自然語言，也不代表
真實 AI 理解品質**。不要將展示輸出視為實際需求分析結果。

### SQLite project and planning-run persistence（M2.1／M2.2-lite）

目前 persistence layer 可保存 `AnalysisProject`，以及一次需求→追問→補充答案→
正式結果的 `PlanningRun`。呼叫端明確開啟、初始化及關閉 connection；import
module 不會自動建立資料庫：

```python
from pathlib import Path

from ai_poc_planner.application import AnalysisProjectService
from ai_poc_planner.persistence import (
    SQLiteProjectRepository,
    database_connection,
    initialize_database,
)

connection = database_connection(Path("local-planner.sqlite3"))
try:
    initialize_database(connection)
    projects = AnalysisProjectService(SQLiteProjectRepository(connection))
    project = projects.create(
        title="客服知識檢索 PoC",
        problem_statement="客服需要更快找到已核准的產品答案。",
    )
    assert projects.load(project.id) == project
finally:
    connection.close()
```

資料庫目前為 SQLite `PRAGMA user_version = 2`；fresh database 直接建立 v2，既有
v1 database 可在保留 `analysis_projects` 的情況下新增 `planning_runs`。結構化
intent、追問、答案、assessment 與 proposal 使用 JSON `TEXT`，載入時一律重新經
Pydantic 驗證；Markdown 保存為 `TEXT`。本里程碑沒有 ORM 或通用 migration
framework。測試使用 temporary SQLite files，repository 不會被 offline demo 自動啟用。

本次驗證環境：Python 3.12.10、Pydantic 2.13.4、pytest 9.1.1、ruff
0.15.22。`pyproject.toml` 使用相容版本範圍，避免把專案綁死在單一 patch
版本。

案例查找目前只是三筆 Python synthetic fixtures 的 deterministic filter，固定
similarity 僅供流程展示；它不是 embeddings、semantic search 或 FAISS。

目前限制：訪談資料與案例均為固定 fixture；PlanningRun 只支援依目前問題批次逐步補答，
不提供完整 interview turns、conversation checkpoints、arbitrary resume
或 session replay。FastAPI persisted endpoints 與單頁 Streamlit fake-mode UI 已實作，
但仍沒有 live chat-model provider runtime、FAISS、Docker、production security 或
production deployment。

## 安全與隱私

- 不提交 `.env`、API keys、本機資料庫、FAISS 索引、trace、訪談內容或輸出報告。
- `.env.example` 只放變數名稱與安全假值。
- 高影響決策只允許輔助用途，必須保留具實質意義的人類審核。
- 本專案提供 PoC 規劃輔助，不提供法律、醫療、信用或人事最終決策。

## License

[MIT](LICENSE)
