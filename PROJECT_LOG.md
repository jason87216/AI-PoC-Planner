# Project Log

## Current Goal

執行 `feat/offline-vertical-slice` batch：先完成 M1.4，再建立不使用網路、API key、SQLite、FAISS、LangChain、API 或 UI 的純 application/service 離線流程。

## Current Status

- Batch scope（2026-07-19）：`訪談 fixture → fake provider structured facts/tool inputs → 六組 deterministic tools → M1.3 assessment → proposal → Markdown → CLI demo`。
- 本批次明確不實作 SQLite persistence，因此 M2.1～M2.5 的 application/service 能力可落地，但含 repository／reload 的正式 TASKS 驗收仍保持未完成，不會誤標為完成。
- M1.3 已推送至 `origin/main`；後續工作位於 `feat/offline-vertical-slice`。

- `SPEC.md`、`PLAN.md` 與 `TASKS.md` 已於 2026-07-19 獲使用者核准為第一版 implementation baseline。
- 第一版規格已建立 baseline commit：`d5fc880 docs: establish specification baseline`。
- M1.1 已建立 Python package、domain contracts、provider Protocol、fake provider 與離線測試。
- Python 3.12 下 editable install、13 個 pytest、ruff 與 smoke command 全部通過。
- 專案已初始化為獨立 Git repository。
- M1.1 已建立 `feat: add project skeleton and offline domain contracts` commit。
- 公開 GitHub repository 與 `origin` 已於先前授權工作中建立；M1.3 本輪不 push。
- M1.2 已獲使用者授權，開始前的 13 個既有測試均通過。
- M1.2 contract tests 80 個、完整測試 93 個、ruff 與 smoke command 全部通過。
- M1.2 使用獨立 commit message：`feat: complete workflow and persistence contracts`。
- M1.3 新增 119 個離線 rule/engine tests；完整測試共 212 個。
- M1.3 使用獨立 commit message：`feat: implement scoring and hard-gate engine`，不 push。
- M1.4 已將 provider boundary 收斂為 `prepare_assessment`，只回傳 typed facts／tool inputs 或追問；正式 assessment 決策仍由 M1.3 掌握。
- 新增 deterministic fake embeddings seam；它不是 semantic embeddings，也未接入 FAISS。
- M1.4 完整 suite 為 218 passed，Ruff 與 provider smoke 通過。
- 離線 batch 已實作六組 typed deterministic tool services；案例查找為明確 fixture filter，不是 embeddings／FAISS／semantic search。
- Tool services 只產生 M1.2 output envelopes；正式 weighted score 與 recommendation 仍只由 M1.3 engine 計算。
- 六組 tools 完成後完整 suite 為 229 passed，Ruff 通過。

## M1.3 Data Flow and Contract Mapping

```text
AssessmentInput
  ├── stable assessment ID／UTC evaluated_at
  ├── typed AssessmentFacts
  ├── six typed tool outputs
  └── project/session-owned EvidenceReference records
        ↓
six pure rubric functions → Decimal weighted contributions／total
        ↓
HG-01..HG-07 → blocked > assistive_only > requires_controls > pass
        ↓
75／55 thresholds with gate caps
        ↓
immutable Assessment with recommendation and decision trace
```

- `SCORE_WEIGHTS` remains the only weight table; engine and contracts import it.
- Tool-declared ratings are retained for M1.2 compatibility but are never trusted as final scores.
- `AssessmentInput` gained optional typed evaluation fields so intermediate workflow state remains valid; `assess_project` requires them all.
- `Assessment` gained required `recommendation`; `HardGateResult` gained `evidence_refs`.
- Missing tools, tool errors, unknown/cross-session evidence and contradictory declared gate results raise stable `AssessmentError` codes.
- M1.3 實際涉及 18 個檔案，超過一般 3–5 檔案原則；原因是核准任務同時要求 domain facts、三個 assessment 模組、三組測試與四份治理文件同步，且未加入任何 M1.4 infrastructure。
- 審查後補強 tool evidence registry 驗證、重複 facts 一致性、一般自主企業操作與必要 security／governance／audit controls，並以明確 owner 欄位取代 metadata 慣例。

## M1.2 Contract Mapping

| SPEC contract | 現有 model | 本輪新增或修改 |
|---|---|---|
| `AnalysisProject` | 已有 | 保留；共用 UTC／ID 驗證型別 |
| `InterviewSession` | 無 | 新增 session、stage、turn reference 與順序驗證 |
| `InterviewTurn` | 已有 | 保持相容，改用遞迴 `JSONValue` 與共用 UTC 型別 |
| `ConversationStateSnapshot` | 無 | 新增可 round-trip 的 append-oriented snapshot |
| `CaseMetadata` | 無 | 新增 SQLite-ready metadata contract，不建立 repository |
| `Assessment` | 無 | 新增六維度、gate、evidence 與 rule-version result contract |
| `PocProposalRecord` | 無 | 新增 validated proposal persistence payload |
| `ReportExport` | 無 | 新增 Markdown export metadata contract |
| Agent state | 無 | 新增 framework-neutral `AgentState` 與 reference consistency 驗證 |
| 六個 tool interfaces | 無 | 新增六組獨立 input/output contracts，不實作 tools |
| Evidence／source reference | 字串 refs | 新增結構化 `EvidenceReference`，保留既有字串欄位相容性 |
| `JSONValue` | 僅 scalar／`list[str]` | 收窄為嚴格、可遞迴的 JSON 值；拒絕任意 Python objects |
| `PocProposal` invariants | 已有 | 保留結構一致性；計分、gate precedence、推薦決策留給 M1.3 |

M1.2 因使用者明確要求一次完成 persistence、workflow、Agent state、十二個
tool contracts、測試與文件同步，共涉及 11 個檔案；這是 `AGENTS.md`「原則上
不超過五檔」的已記錄任務範圍例外，未擴張到任何執行引擎或 infrastructure。

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
- 2026-07-19：完成 M1.2 persistence/workflow/Agent-state 與六組 tool contracts；明確把計分、gate precedence 與推薦決策保留給 M1.3。
- 2026-07-19：規格複審後將六種 tool output 收斂為互斥的成功／`ToolError` envelope，並補齊 Agent 追問去重驗證。
- 2026-07-19：完成 M1.3 六維 rubric、Decimal 權重、HG-01～HG-07、recommendation mapping 與離線 assessment engine。

## Git Notes

- Repository root：`D:\ai_class\projects\AI PoC Planner`。
- 本專案使用自己的 `.git`，不再依附 `D:\ai_class` 上層 repository。
- GitHub remote 為 `origin`（公開 `jason87216/AI-PoC-Planner`）；M1.3 明確不 push。
- M1.3 commit 完成後本機 history 為四個 commits，`main` 將領先 `origin/main` 一個 commit。

## Known Problems

- FastAPI、Streamlit、SQLite、FAISS、LangChain Agent、Docker 與真實 provider 尚未實作。
- 真實 chat model 與 embeddings model 的預設選擇留待對應 provider task 確認；M1.1 只提供 fake provider。
- 部分 hard gate 在真實企業環境中需要法務、資安與領域專家核准，不能只由模型決定。
- 多語言報告與 PDF 匯出不在 MVP 範圍。
- 部分 hard-gate facts 仍需由後續訪談／tool adapters 可靠產生；M1.3 不以文字猜測填補。

## Next Steps

1. 等待 M1.4 的明確授權，不提前擴充 provider／embeddings interfaces。
2. 後續 application service 直接呼叫 M1.3 `assess_project`，不得讓 provider 覆寫正式分數或 gates。

## Handoff Summary

新工作階段應先閱讀 `AGENTS.md`、本檔與 `docs/spec/`。M1.3 已完成；目前沒有 M1.4 授權，不得提前建立新 provider／embeddings、資料庫或垂直切片。
