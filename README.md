# AI PoC Planner

AI PoC Planner 是一個規格中的公開 AI 工程作品：透過單一 LangChain Agent 進行結構化需求訪談，結合本機案例檢索、固定評分框架與風險 hard gates，產生可追蹤、可測試、可匯出的 AI 導入 PoC 建議。

> 專案狀態：**deterministic offline vertical slice + M2.1 SQLite project
> persistence available**。固定訪談資料到 Markdown 報告的 demo 仍是完全
> in-memory；另提供 analysis project 的 SQLite create／load 邊界，兩者皆不需要
> API key 或網路。

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

### SQLite analysis project persistence（M2.1）

目前 persistence layer 只保存 `AnalysisProject`。呼叫端明確開啟、初始化及關閉
connection；import module 不會自動建立資料庫：

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

資料庫 schema 以 SQLite `PRAGMA user_version = 1` 驗證；本里程碑沒有 ORM、
migration upgrade chain 或其他 entity 資料表。測試使用 temporary SQLite files，
repository 不會被 offline demo 自動啟用。

本次驗證環境：Python 3.12.10、Pydantic 2.13.4、pytest 9.1.1、ruff
0.15.22。`pyproject.toml` 使用相容版本範圍，避免把專案綁死在單一 patch
版本。

案例查找目前只是三筆 Python synthetic fixtures 的 deterministic filter，固定
similarity 僅供流程展示；它不是 embeddings、semantic search 或 FAISS。

目前限制：訪談資料與案例均為固定 fixture；只有 analysis project 可持久化，
訪談、conversation state、assessment、proposal 與 report 尚未持久化，也不支援
resume。FastAPI、Streamlit、FAISS、LangChain／LangGraph Agent、Docker、真實
OpenAI-compatible provider、production security 與 production deployment 均尚未
實作，因而目前沒有 API 或 UI 啟動命令。

## 安全與隱私

- 不提交 `.env`、API keys、本機資料庫、FAISS 索引、trace、訪談內容或輸出報告。
- `.env.example` 只放變數名稱與安全假值。
- 高影響決策只允許輔助用途，必須保留具實質意義的人類審核。
- 本專案提供 PoC 規劃輔助，不提供法律、醫療、信用或人事最終決策。

## License

[MIT](LICENSE)
