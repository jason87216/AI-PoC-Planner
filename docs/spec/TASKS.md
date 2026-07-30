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
  llama.cpp full compatibility gate 現在先於付費 NVIDIA workflow；仍沒有通過的
  dual-endpoint live artifact，P7.2a checkpoint 仍 pending。

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
