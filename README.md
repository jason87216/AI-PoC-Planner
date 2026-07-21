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

目前限制：訪談資料與案例均為固定 fixture；PlanningRun 只支援一批追問答案後
繼續執行，不提供完整 interview turns、conversation checkpoints、arbitrary resume
或 session replay。FastAPI planning endpoint 與 LangChain 單一 Agent 已實作，但沒有
live chat-model provider runtime；Streamlit、FAISS、Docker、production security 與
production deployment 仍未實作，因此目前沒有 production API 或 UI 啟動命令。

## 安全與隱私

- 不提交 `.env`、API keys、本機資料庫、FAISS 索引、trace、訪談內容或輸出報告。
- `.env.example` 只放變數名稱與安全假值。
- 高影響決策只允許輔助用途，必須保留具實質意義的人類審核。
- 本專案提供 PoC 規劃輔助，不提供法律、醫療、信用或人事最終決策。

## License

[MIT](LICENSE)
