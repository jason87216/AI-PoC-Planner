# Project Log

## Current Goal

依核准的第一版規格基準完成、驗證並提交 `TASKS.md` 的 M1.1；本輪已停止於此任務。

## Current Status

- `SPEC.md`、`PLAN.md` 與 `TASKS.md` 已於 2026-07-19 獲使用者核准為第一版 implementation baseline。
- 第一版規格已建立 baseline commit：`d5fc880 docs: establish specification baseline`。
- M1.1 已建立 Python package、domain contracts、provider Protocol、fake provider 與離線測試。
- Python 3.12 下 editable install、13 個 pytest、ruff 與 smoke command 全部通過。
- 專案已初始化為獨立 Git repository。
- M1.1 已建立 `feat: add project skeleton and offline domain contracts` commit。
- 未設定 remote、未建立 GitHub repository，也未 push。

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
- 2026-07-19：以 Python 3.12.10 完成 editable install；實際主要依賴為 Pydantic 2.13.4、pytest 9.1.1、ruff 0.15.22。
- 2026-07-19：完成 M1.1 contracts、fake provider、13 個離線測試及 smoke command，並建立 implementation commit。

## Git Notes

- Repository root：`D:\ai_class\projects\AI PoC Planner`。
- 本專案使用自己的 `.git`，不再依附 `D:\ai_class` 上層 repository。
- 目前有兩個本機 commit；沒有 remote、GitHub repository 或 push。

## Known Problems

- FastAPI、Streamlit、SQLite、FAISS、LangChain Agent、Docker 與真實 provider 尚未實作。
- 真實 chat model 與 embeddings model 的預設選擇留待對應 provider task 確認；M1.1 只提供 fake provider。
- 部分 hard gate 在真實企業環境中需要法務、資安與領域專家核准，不能只由模型決定。
- 多語言報告與 PDF 匯出不在 MVP 範圍。

## Next Steps

1. 等待 M1.2 的新指示，不提前建立評分或 hard-gate 引擎。
2. M1.2 開始前確認其剩餘範圍：完整 persistence／Agent-state／tool contracts，以及是否需要遞迴 JSON value。

## Handoff Summary

新工作階段應先閱讀 `AGENTS.md`、本檔與 `docs/spec/`。規格 baseline 與 M1.1 已完成；目前沒有 M1.2 授權，不得提前建立評分引擎、資料庫或垂直切片。
