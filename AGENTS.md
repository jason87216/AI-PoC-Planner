# Project Agent Rules

## Project Overview

AI PoC Planner 是公開作品集型專案。產品透過單一 LangChain Agent 進行結構化需求訪談、案例檢索、固定評分與 hard-gate 判定，輸出可驗證的 AI PoC 建議與 Markdown 報告。

目前處於規格階段。除非使用者明確核准進入 implementation，否則不要建立正式應用程式碼。

## Tech Stack

- Python
- FastAPI、Streamlit
- LangChain `create_agent`、Tool Calling、Pydantic Structured Output
- SQLite、FAISS
- pytest、deterministic fake model
- Docker Compose
- OpenAI-compatible provider adapter
- MIT License

MVP 禁止加入 PostgreSQL、pgvector、Qdrant、雲端向量資料庫、多 Agent、多租戶或雲端部署。

## Project Commands

<!-- BEGIN MANAGED:PROJECT_COMMANDS -->
目前尚無可執行的專案命令。下列命令只有在 `pyproject.toml` 與對應入口由 TASKS 核准建立後才生效：

- Setup: `uv sync --all-groups`
- Run API: `uv run uvicorn app.main:app --reload`
- Run UI: `uv run streamlit run ui/app.py`
- Build: TODO；MVP 為 Python 應用，Docker image 建置命令需在 Dockerfile 建立後確認。
- Test: `uv run pytest`
- Lint: `uv run ruff check .`
<!-- END MANAGED:PROJECT_COMMANDS -->

## Project Structure

- `deep-research-report.md`: 經公開來源查證的研究基礎。
- `docs/spec/SPEC.md`: 產品、資料、Agent、工具、API、安全與驗收契約。
- `docs/spec/PLAN.md`: 依賴順序、垂直切片、測試與 Definition of Done。
- `docs/spec/TASKS.md`: Must／Should／Could 實作任務。
- `README.md`: 公開且安全的專案入口。
- `PROJECT_LOG.md`: 狀態、決策、問題與交接。
- `.env.example`: 可提交的環境變數範例；不得放真實秘密。

## Coding Rules

- 規格先行；行為或資料契約改變時先更新 `docs/spec/`。
- 核心 domain 與評分邏輯保持 deterministic，不把規則藏在 prompt。
- 使用 Pydantic models 定義 API、tool input/output 與報告契約。
- 模型只能透過 provider adapter 取得；不得在 domain 或 Agent workflow 硬編碼模型名稱。
- SQLite 儲存業務資料；FAISS 只儲存 embeddings 與向量 ID。
- 優先小型垂直切片，每個任務原則上修改不超過五個檔案。
- 新增或修正行為時同步加入 pytest；外部模型測試必須可由 fake model 取代。

## Security Rules

- 不顯示、提交或記錄完整 API key、token、密碼、cookie 或訪談敏感內容。
- 不提交 `.env`、`*.db`、`*.sqlite*`、FAISS indexes、trace、logs 或使用者輸出報告。
- Tool Calling 在 MVP 內只能呼叫本機純評估／檢索工具，不得操作真實企業系統。
- hard gates 必須先於一般評分，且不得被高商業價值分數覆蓋。
- 高影響人事、醫療、法律、信用或財務決策只允許 assistive-only，保留人工最終決策。
- 不將 Streamlit session state 當成可信或唯一的持久化來源。

## Git Rules

- 本資料夾是獨立 Git repository；不要修改或提交上層 `D:\ai_class` repository 的檔案。
- 有意義的修改前後檢查 `git status`。
- 不使用 `git add .`；只 stage 明確檔案。
- 未獲明確授權不得 commit、設定 remote、建立 GitHub repository 或 push。
- commit 前檢查 staged diff 與秘密／本機資料檔案。
- Git 初始化、branch、remote、commit 等工作流變更後更新 `PROJECT_LOG.md`。

## Completion Checklist

- [ ] 功能符合 `SPEC.md` 與 TASKS 驗收條件。
- [ ] 相關 pytest、contract、trajectory 與 fake-model 測試通過。
- [ ] hard gates 與加權評分有獨立測試。
- [ ] `PROJECT_LOG.md` 已更新。
- [ ] `TASKS.md` 狀態已更新。
- [ ] README／命令文件在流程改變時已同步。
- [ ] 無秘密、本機資料庫、索引、trace 或使用者資料被 stage。

## Inherited Workspace Rules

<!-- BEGIN MANAGED:INHERITED_WORKSPACE_RULES source="workspace AGENTS.md" -->
### Inherited Workspace Boundary

- Stay within the current project or explicitly authorized workspace scope.
- Do not read, search, edit, or summarize files outside the project without explaining why.
- If wider workspace context is needed, read documented project/workspace instructions rather than scanning unrelated folders.

### Inherited Secret Safety

- Never display complete API keys, tokens, passwords, cookies, private keys, or auth file contents.
- Mask secrets in any report.
- Never commit `.env`, private keys, auth files, local databases, logs, installers, dependency folders, or local tool state.
- If a real secret may have leaked, stop and report the platform plus recommended revoke/regenerate action.

### Inherited Git Safety

- Check `git status` and staged diff before any commit.
- Do not use `git add .` by default; prefer specific files.
- Do not commit unless the user explicitly confirms.
- Do not push to a remote unless the user explicitly asks.
- Do not rewrite Git history without explaining the impact and getting confirmation.
- Update `PROJECT_LOG.md` after meaningful Git setup or repository workflow changes.

### Inherited High-Risk Operations

Explain impact and obtain confirmation before deleting or bulk-moving files, modifying real `.env` or auth stores, changing global tools, installing global software, changing Git remotes/history, overwriting substantial human documentation, or making broad structural changes.

### Inherited Project Bootstrap Defaults

- Use project bootstrap before creating files for a new project.
- Use specification-first workflow for formal or complex projects.
- Do not generate application code unless explicitly requested.
- Never fabricate commands; unresolved commands remain TODO.
- Do not create the first commit, remote, GitHub repository, or push without explicit authorization.
<!-- END MANAGED:INHERITED_WORKSPACE_RULES -->
