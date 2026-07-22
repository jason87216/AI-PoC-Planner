# Project Log

## Current Goal

等待審核 M2.5 persisted planning flow；不擴張至 live provider、Streamlit、FAISS 或新的 proposal integration。

## Current Status

- M2.4-lite 已完成：單一 LangChain `create_agent` 從自然語言與補答產生 `PlanningIntent`，呼叫唯一 typed planning tool；工具實際組合既有 catalog matching 與 deployment posture service。FastAPI 提供 `GET /health` 與 `POST /v1/planning/interpret`，回傳工具實際結果與最多四題固定繁中追問。
- M2.5 persisted planning flow 已完成：最小 FastAPI run create／clarification／read endpoints 組合 LangChain intent、既有 PlanningRun service/coordinator 與正式 deterministic assessment pipeline。每批最多四題，允許第二批 formal-assessment 追問；schema v2 不變。
- M2.4 stateless endpoint 不建立或更新 `PlanningRun`，不產生六維 score、recommendation、hard gate、proposal 或 Markdown；M2.5 另以既有 persisted workflow 保存正式結果。FastAPI composition 一律由外部注入 LangChain chat model，沒有 live provider runtime。
- 自動測試與 `python -m ai_poc_planner planning-demo` 使用 scripted LangChain official fake chat model，僅證明 Agent orchestration 與 typed tool integration，不宣稱自然語言理解品質。
- M2.3-lite contracts／fixture slice 已從 PR #3、PR #4 合併後的 main 建立；正式 catalog 僅九類，非 AI alternatives 與 deployment contract 骨架均保持不決定正式評分、recommendation 或 hard gates。
- PR #2 已於 2026-07-20 以 merge commit `a5b3bbb` 合併；`feat/planning-run-persistence` 從該同步基準建立。
- M2.2-lite 已完成 `PlanningRun` 四狀態 contract、SQLite `planning_runs`、schema v1→v2、create/get/update/list repository、application service 與 persisted offline coordinator。
- 模糊需求會保存四個追問；補充一批答案後可完成並重新讀取同一份 assessment、proposal 與 Markdown。完整 suite 為 311 passed，Ruff 與 in-memory demo 通過。
- M2.2-lite scope adjustment 已核准：展示版先完成需求→追問→正式結果→保存／重讀閉環；完整 interview turns、arbitrary resume、conversation checkpoints、Agent-state history 與 session replay 移至 Roadmap。
- 下一個精簡任務是 common AI implementation pattern catalog；本輪不執行。
- M2.1 建立的 project schema 已由 M2.2-lite 升級至 `PRAGMA user_version = 2`；v1 database 可保留 projects 並新增 planning runs。
- `AnalysisProject` 六個正式欄位會以獨立 columns 保存並重新經 Pydantic 驗證；UUID 使用 canonical string、status 使用 enum value、timestamps 使用 ISO 8601 UTC。
- M2.1 integration suite 為 25 passed；完整 suite 為 281 passed。沒有新增 runtime dependency，也沒有建立 tracked SQLite file。
- 本輪明確不包含完整訪談 turns、state snapshot、arbitrary resume 或 session replay。
- Batch scope（2026-07-19）：`訪談 fixture → fake provider structured facts/tool inputs → 六組 deterministic tools → M1.3 assessment → proposal → Markdown → CLI demo`。
- 2026-07-19 offline batch 當時未含 SQLite；其 PR #1 已 merge。M2.1 已由 PR #2 merge，M2.2-lite 位於獨立 feature branch。

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
- `run_offline_planning(OfflinePlanningRequest)` 已串接 project、固定 interview、fake provider、六組 tools、M1.3 assessment、proposal、Markdown 與可選檔案輸出。
- CLI：`python -m ai_poc_planner demo [--output PATH]`；預設輸出至 ignored `artifacts/demo-report.md`。
- pass／blocked／assistive-only／requires-controls、provider／tool／clarification／evidence／report errors 皆有 application tests；review 修正後完整 suite 為 256 passed。
- 兩軸 review 修正 tool-input／facts 矛盾檢查、invalid provider structured output、scope assumptions／時程／團隊報告，以及 Markdown markup neutralization／secret-like key redaction。
- 本次使用者明確核准長批次與 2–4 commits，實際跨 32 個檔案；超過一般單任務五檔原則，原因是同一 tracer slice 同時包含 provider、六 tools、workflow、proposal、report、CLI、測試、文件與 repo-wide format gate，且未跨入明確禁止的 infrastructure。

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

- 2026-07-21: Completed the minimal LangChain + FastAPI offline planning slice. One typed tool combines deterministic opportunity matching and deployment posture evaluation; the API has safe 422／502／500 envelopes and fixed bounded clarification questions.
- 2026-07-21: Completed the persisted FastAPI planning flow. Saved runs retain only validated intent and business facts; matching/deployment reload from intent without LangChain, while completed assessment/proposal/Markdown remain exact persisted values.
- 2026-07-21: Completed M2.3-lite catalog matching and deployment-posture assessment. The fixed nine-entry catalog now has direct deterministic matching, separate non-AI directions, and limited posture guidance; scoring, hard-gate and proposal integration remain deferred.

- 2026-07-20：核准 M2.2-lite scope adjustment，保留原完整 conversation-resume 規劃於 Roadmap，不刪除既有 contracts。
- 2026-07-20：完成 PlanningRun contract、SQLite v1→v2、repository/service/coordinator 與 30 個高價值測試；完整 suite 311 passed。
- 2026-07-20：PR #2 以一般 merge commit `a5b3bbb` 合併並從同步 main 建立 `feat/planning-run-persistence`。
- 2026-07-20：完成 M2.1 SQLite project schema、create/load repository、application service 與 temporary-file integration tests。
- 2026-07-20：以明確 transaction commit／rollback、caller-owned connection 與 stable errors 隔離 `sqlite3` 低階例外。
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
- GitHub remote 為 `origin`（公開 `jason87216/AI-PoC-Planner`）。
- PR #2 merge commit 為 `a5b3bbb`；目前 branch 為 `feat/planning-run-persistence`，建立 Draft PR 前沒有 upstream 是正常狀態。

## Known Problems

- SQLite 目前保存 `AnalysisProject` 與精簡 `PlanningRun`；完整 interview turns、conversation checkpoints、arbitrary resume 與 replay 尚未實作。
- FastAPI planning endpoint 與 LangChain single Agent 已實作；Streamlit、FAISS、Docker 與真實 provider 仍未實作。API 沒有 production startup composition，因為 chat model 必須由呼叫端明確注入。
- 真實 chat model 與 embeddings model 的預設選擇留待對應 provider task 確認；M1.1 只提供 fake provider。
- 部分 hard gate 在真實企業環境中需要法務、資安與領域專家核准，不能只由模型決定。
- 多語言報告與 PDF 匯出不在 MVP 範圍。
- 部分 hard-gate facts 仍需由後續訪談／tool adapters 可靠產生；M1.3 不以文字猜測填補。

## Next Steps

1. 等待 M2.5 persisted planning flow 人工審核；本輪不擴張至 provider、Streamlit、FAISS 或新的 proposal integration。
2. 完整 turn/session/checkpoint replay 留在 Roadmap；不得以此 API slice 擴張。
3. 後續 persistence 必須包在既有 application boundaries 外，不得讓 provider 覆寫 M1.3 分數、gates 或 recommendation。

## Handoff Summary

新工作階段應先閱讀 `AGENTS.md`、本檔與 `docs/spec/`。M2.4-lite 已提供最小、無狀態的 LangChain + FastAPI planning slice；不可把它誤接至 PlanningRun completed、正式評分、hard gates、proposal 或 report。下一步需先等待人工審核，不得提前跳到真實 provider、Streamlit、FAISS 或 UI。
