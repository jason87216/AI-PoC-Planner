# Project Log

## Current Goal

依核准的第一版規格基準開始 implementation，目前僅執行 `TASKS.md` 的 M1.1。

## Current Status

- `SPEC.md`、`PLAN.md` 與 `TASKS.md` 已於 2026-07-19 獲使用者核准為第一版 implementation baseline。
- 研究報告、bootstrap 文件與 `docs/spec/` 已完成一致性整理。
- 專案已初始化為獨立 Git repository。
- 正在建立純文件 baseline commit；不設定 remote、不建立 GitHub repository，也不 push。

## Important Decisions

- MVP 使用 Python、FastAPI、Streamlit、LangChain 單一 Agent、Tool Calling 與 Pydantic Structured Output。
- SQLite 儲存專案、訪談、評估及案例 metadata；FAISS 儲存案例 embeddings。
- PostgreSQL、pgvector、Qdrant 與雲端向量資料庫只列入 Roadmap。
- 模型經 provider adapter 注入，預設支援 OpenAI-compatible API；fake model 支援離線測試。
- 六項加權評分合計 100%；hard gates 優先於加權分數。
- 採用 MIT License。

## Recent Changes

- 2026-07-19：完成 `deep-research-report.md` 的公開發布前查證與引用清理。
- 2026-07-19：移除內部引用標記，改為可公開存取的標準 Markdown links。
- 2026-07-19：移除無法由第一手來源可靠確認的競品敘述。
- 2026-07-19：統一 SQLite + FAISS 架構、評分框架與 Docker 安全邊界。
- 2026-07-19：建立 bootstrap 文件及 `docs/spec/` 規格文件。
- 2026-07-19：在專案根目錄完成 `git init`。
- 2026-07-19：規格審核通過，核准進入 M1.1；分支調整為 `main`。

## Git Notes

- Repository root：`D:\ai_class\projects\AI PoC Planner`。
- 本專案使用自己的 `.git`，不再依附 `D:\ai_class` 上層 repository。
- 尚無 commit、remote、GitHub repository 或 push。

## Known Problems

- 尚未建立 `pyproject.toml` 或任何正式應用程式碼；README 與 AGENTS 中的指令均標示為 planned。
- 實際預設 chat model 與 embeddings model 尚待第一個 implementation task 確認。
- 部分 hard gate 在真實企業環境中需要法務、資安與領域專家核准，不能只由模型決定。
- 多語言報告與 PDF 匯出不在 MVP 範圍。

## Next Steps

1. 只完成 M1.1：最小 Python 可執行骨架、domain contracts 與 fake-model 離線測試。
2. 執行安裝、pytest 與 smoke command 驗證。
3. 完成 M1.1 commit 後停止，等待 M1.2 的新指示。

## Handoff Summary

新工作階段應先閱讀 `AGENTS.md`、本檔與 `docs/spec/`。規格 baseline 已核准，但目前授權範圍只有 M1.1，不得提前進入 M1.2 或垂直切片。
