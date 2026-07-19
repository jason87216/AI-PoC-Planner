# AI PoC Planner

AI PoC Planner 是一個規格中的公開 AI 工程作品：透過單一 LangChain Agent 進行結構化需求訪談，結合本機案例檢索、固定評分框架與風險 hard gates，產生可追蹤、可測試、可匯出的 AI 導入 PoC 建議。

> 專案狀態：**Specification only（僅完成研究與規格，尚未建立正式應用程式碼）**

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

## 開發命令

目前尚未建立 `pyproject.toml` 或程式碼骨架，因此下列命令只是已決策的目標介面，**目前不可執行**：

| 目的 | 規劃命令 | 生效條件 |
|---|---|---|
| 安裝 | `uv sync --all-groups` | TASKS 的專案骨架任務建立 `pyproject.toml` 後 |
| API | `uv run uvicorn app.main:app --reload` | FastAPI 入口完成後 |
| UI | `uv run streamlit run ui/app.py` | Streamlit 入口完成後 |
| 測試 | `uv run pytest` | pytest 設定與首批測試完成後 |
| Lint | `uv run ruff check .` | ruff 加入開發依賴後 |

## 安全與隱私

- 不提交 `.env`、API keys、本機資料庫、FAISS 索引、trace、訪談內容或輸出報告。
- `.env.example` 只放變數名稱與安全假值。
- 高影響決策只允許輔助用途，必須保留具實質意義的人類審核。
- 本專案提供 PoC 規劃輔助，不提供法律、醫療、信用或人事最終決策。

## License

[MIT](LICENSE)
