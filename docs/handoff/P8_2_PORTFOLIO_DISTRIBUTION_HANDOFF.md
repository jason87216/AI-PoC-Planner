# P8.2 Portfolio Distribution Quickstart Handoff

## Current repository state

- Repository: `jason87216/AI-PoC-Planner`
- Base branch: `main`
- Current branch: `codex/p8-1b2-uat-product-fixes`
- PR #29: Open / Ready for review after this closeout; not merged
- Current accepted HEAD: `70e327d724bb7b677d355691be2dd8a9822c44a5`
- Planning schema: v9 (`planning_projects.archived_at`)
- Current offline baseline: `867 passed, 7 skipped` (opt-in live tests)

## Completed baseline

- FastAPI／Streamlit local workflow with persisted project, discovery, assessment and report state
- Project history actions: continue/view, confirmed-only copy, and user-facing delete backed by data-layer archive
- Schema v9 additive migration and active-project fail-closed guards
- Local runtime start／status／stop scripts
- Single OpenAI-compatible provider boundary and project-bound model profiles
- P7.2a: Complete；P7.2b: Pending；P7.2 overall: Incomplete
- P8.1a: Complete；P8.1b-1: Complete；P8.1b-2 and P8.1b overall: Complete
- `governed_access` evidence is synthetic portfolio fixture data, not company employee or permission data

## Existing runtime commands

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\start-local.ps1 -Mode Uat
.\scripts\status-local.ps1 -Mode Uat
.\scripts\stop-local.ps1 -Mode Uat
```

The current `.venv` prerequisite is a local development/runtime environment; it is not committed.

## Missing distribution capability

- Fresh-download setup
- Automatic `.venv` creation
- Dependency installation
- Friendly root-level launch／stop entrypoints
- Clean setup failure guidance
- Release ZIP validation

## Proposed P8.2 goal

下載 ZIP
→ 執行一次 setup
→ 建立隔離環境
→ 安裝依賴
→ 啟動 UI
→ 日後可使用簡單啟動／關閉入口

## Safety boundaries

- 不修改系統 Python
- 不安裝或更新 CUDA
- 不安裝 GPU driver
- 不安裝或下載 provider／模型
- 不安裝 Docker
- 不寫入全局 PATH
- 不讀取或輸出 API key
- 不提交 `.venv` 或 private runtime state
- 不啟動 P7.2b
- 不宣稱 consumer installer 已完成

## Questions P8.2 must resolve

- Python 3.12 prerequisite policy
- `setup.ps1` idempotency
- Dependency lock／installation mode
- Root-level `.cmd`／`.ps1` launchers
- ZIP extraction path handling
- Upgrade／repair behavior
- Uninstall or cleanup scope
- GitHub Release artifact boundary

## Recommended first checkpoint

**P8.2a：Windows portfolio quickstart，非正式安裝程序**
