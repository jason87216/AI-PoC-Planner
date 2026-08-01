# Tasks: viable MVP

## Status legend

- **Complete**: implemented and merged or accepted as the current baseline.
- **Next**: the next bounded implementation target.
- **Pending**: planned but blocked by an earlier checkpoint.
- **Deferred**: intentionally outside the current MVP path.

Fake providers are permitted only for deterministic automated tests. They are not valid product-acceptance evidence and must never become a silent runtime fallback.

## Phase 0 — Specification reset

### S0.1 Approve viable-MVP specification package — Complete

- Real-provider-first product boundary established.
- Formal analysis requires a project-bound, enabled, tested model profile.

## Phase 1 — Model profiles and OpenAI-compatible connection

### P1.1–P1.5 — Complete

- Safe model-profile contracts and local persistence.
- Single OpenAI-compatible provider adapter.
- Readiness guard, connection test and safe provider status.
- Opt-in real-provider integration coverage.

## Phase 2 — Project versions, conversation and facts

### P2.1–P2.3 — Complete

- Durable projects and immutable completed versions.
- Visible conversation and append-only confirmed-fact revisions.
- SQLite persistence without prompts, reasoning traces or raw provider responses.

## Phase 3 — Discovery

### P3.1–P3.3 — Complete

- Minimal brief, requirement understanding, correction and confirmation.
- At most three interview rounds with at most three contextual questions per round.
- Durable reload and unknown／missing fact handling.

## Phase 4 — Assessment

### P4.1–P4.3 — Complete

- Structured AI／non-AI／hybrid／foundations-first options.
- Evidence-backed six-dimension ratings.
- Deterministic recommendation category, weighted total and HG-01 through HG-07.

## Phase 5 — Reviewed cases and report

### P5.1 Reviewed local cases — Complete

- Source-backed, approved reviewed-case catalog.
- Deterministic matching and source validation.

### P5.2 Persisted Markdown planning report — Complete

- Structured provider narration with strict validation.
- Program-owned conclusions, scores, gates and case attribution.
- Immutable report persistence and Markdown download.

## Phase 6 — FastAPI／Streamlit product workflow

### P6.1 Home, history and model settings — Complete

### P6.2 Brief, confirmation and interview — Complete

### P6.3 Analysis and readable report views — Complete

### P6.4 Discovery UX closeout — Complete, merged in PR #20

### P6.5 Case-centred results closeout — Complete, merged in PR #22

### P6.6 Product acceptance baseline — Complete, merged in PR #23

- Four Traditional Chinese golden scenarios are the provider-regression baseline.
- Product-owner wording and portfolio review remain Phase 8 work.

### P6.7 Results narrative and comparison redesign — Complete, merged in PR #24

Delivered:

- article-style Results narrative and integrated comparison;
- reviewed solution／case catalog consistency;
- deterministic solution–case–project validation;
- one persisted `ReportSynthesis` shared by Results UI and Markdown;
- report persistence, refresh and history re-entry without provider reruns;
- Markdown download parity and safe reader-facing content.

Merge commit: `91bb6b45f9be2249d9cd9edfd11a309bd806f321`.

## Phase 7 — Local runtime and provider compatibility

### P7.1 Local UAT runtime — Complete, merged in PR #21

- Project-owned `.venv` enforcement.
- FastAPI／Streamlit start, status, supervision and stop.
- UI ports `18501-18599` and API ports `18610-18699`.
- No product default on port `8000`.
- Runtime does not install providers or models.

### P7.2a Representative dual-endpoint compatibility — In progress

1. 定義 model-profile capability contract。
2. 統一 readiness、discovery、analysis、report 四條 structured-output 呼叫策略。
3. 支援本機 endpoint 的可空 token。
4. 統一 token／reasoning parameter strategy。
5. 實作有限次 JSON Schema → JSON Object fallback。
6. fallback 後維持嚴格 Pydantic validation。
7. 統一安全且可行動的 errors，不暴露 secrets、Authorization header 或 raw provider response。
8. 完成 NVIDIA readiness／discovery／analysis／report 驗證。
9. 完成 llama.cpp readiness／discovery／analysis／report 驗證。
10. 受控權限申請代表情境端到端 UAT。
11. 確認 reload／history／download 不重新呼叫 provider。
12. 完成 CI 與秘密資料檢查。

Acceptance checkpoint:

- NVIDIA 與一個使用者自行啟動的本機 llama.cpp endpoint，使用同一 adapter 通過一個代表情境。
- deterministic matching、recommendation category、scoring 與 hard gates 不修改。
- P7.2a 通過不得標記完整 P7.2 Complete。
- 第二次 NVIDIA／llama.cpp live UAT 已執行一次：NVIDIA governed_access 完整流程
  先執行且未出現 assertion failure，但 llama.cpp readiness 以 `provider_timeout`
  失敗；相同 adapter contract 在 60 秒 timeout 下於本機 22.178 秒成功，health 與
  model discovery 亦通過。診斷指向原本 10 秒 readiness timeout 過短。
- readiness timeout 修正為預設 60 秒、process-level 可設定至 300 秒，且 local
  llama.cpp full compatibility gate 現在先於 remote NVIDIA endpoint workflow；仍沒有通過的
  dual-endpoint live artifact，P7.2a checkpoint 仍 pending。
- 第三次 dual-endpoint live UAT 已執行一次：llama.cpp readiness 失敗，local-first gate
  阻止 NVIDIA 呼叫（call count=0）；沒有通過的 dual-endpoint artifact。
- sanitized 本機 response-structure diagnosis 確認模型有回傳 JSON object，但 `status`
  不符合 `Literal["ok"]`；1024 tokens 只移除 truncation，`--reasoning off` 仍是錯誤
  contract。timeout 不再視為目前根因，也沒有安排第四次 dual UAT。
- readiness prompt 已改為明確單一 `status="ok"` JSON contract，bounded repair hint 會
  安全列出 Literal／enum allowed values；P7.2a checkpoint 仍 pending。
- Exact OpenAI JSON Schema readiness 已連續 3/3 通過，Discovery 已達
  `ready_for_assessment`；完整本機 workflow 在第二個 `analysis_option_detail` 失敗，兩次
  都以 `finish_reason=length` 用滿 1024 completion tokens。Schema normalization 成功，
  失敗未進入 Pydantic validation；NVIDIA 未呼叫，也沒有執行 dual UAT。
- `analysis_option_detail` logical token budget 已調整為 2048，並保留其他 stage budget、
  timeout、temperature 與 reasoning policy；目前僅完成 offline validation，待重新進行
  明確授權的本機 qualification，P7.2a checkpoint 仍 pending。
- Live harness analysis／report failure 只保留安全 error code、operation、retryable 與
  recorder 的最後 operation/schema/mode/call count，不輸出 response body 或 user action。
- Report-only diagnosis 顯示四個 report provider calls 都是 HTTP 200、JSON Schema
  success、`finish_reason=stop`；兩輪 application semantic validation 都以
  `provider_output_invalid` 失敗並觸發 deterministic degradation fallback。根因是
  report narration schema 允許數字，但 application safeguard 會拒絕部分數字。
- `ProviderReportSectionDraft.content` 現改為禁止 ASCII digits `0-9` 的 provider
  narration contract；persisted `ReportSectionDraft` 保留歷史讀取相容性，`fact_refs`
  仍要求合法 `Fxxx` tokens，deterministic validation 保留。
  本輪只完成 offline validation，尚無通過的 dual-endpoint artifact，P7.2a checkpoint
  仍 pending。
- 獨立 diff review 發現將 digit-free 規則直接套用於 persisted section 會造成既有合法
  報告 reload 的 backward-compatibility regression。現已分離 strict
  `ProviderReportSectionDraft` 與可讀取歷史資料的 `ReportSectionDraft`；Part A/B 使用
  provider DTO，而 `PlanningReportDraft`／`PersistedPlanningReport` 維持 persisted DTO。
  `_validate_refs` 未放寬，並新增 SQLite／restart／history／Markdown offline regression
  coverage；沒有新的 live artifact，P7.2a checkpoint 仍 pending。

### P7.2b Full golden-scenario compatibility matrix — Pending

1. 擴展至四個 golden scenarios。
2. 完成 NVIDIA／llama.cpp compatibility matrix。
3. 驗證 deterministic results provider-independent。
4. 完成 P7.2 產品與技術驗收。

Acceptance checkpoint:

- 四個 golden scenarios 的 readiness、discovery、analysis、report 雙端點矩陣完成。
- 產品與技術驗收通過後，才可將 P7.2 標記為 Complete。

## P7.2 out of scope

- 自動安裝或下載模型；
- Ollama、LM Studio、vLLM 專用 adapter；
- Docker；
- 雲端部署與帳號建立；
- 多 provider business logic；
- deterministic matching、recommendation category、scoring 或 hard-gate 修改；
- `report_synthesis.py` 重構；
- reviewed-case catalog 擴充。

## Phase 8 — Portfolio and release UAT

### P8.1 Product-owner and portfolio acceptance — Pending

- Review Traditional Chinese wording and business usefulness.
- Verify blocked-no-provider behavior and project-bound model selection.
- Verify Discovery, Assessment, Results, reload, history and download.
- Review P7.2 compatibility evidence.
- Complete honest portfolio and release-readiness documentation.

## Deferred

- Consumer installer and release packaging.
- Automatic llama.cpp or model installation.
- Multi-agent, LangGraph, FAISS and Docker.
- Cloud deployment, accounts, online search and multi-tenancy.
- Production-grade credential encryption.
- PDF／DOCX export.
