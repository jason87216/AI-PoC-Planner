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

### P7.2a Representative dual-endpoint compatibility — Complete

#### Confirmed implementation boundaries

- Explicit provider capability profiles drive authentication, token parameters, reasoning parameters, and structured-output mode selection through the shared OpenAI-compatible adapter.
- Readiness, discovery, analysis, and report use the shared structured-output executor with bounded same-mode repair and no silent provider/model/fake fallback.
- Deterministic matching, recommendation category, scoring, hard gates, formal authority/boundary, reviewed-case facts, and persisted report consistency remain program-owned.
- Reload, history, refresh, Markdown download, duplicate operations, and restart read persisted state without provider calls. No SQLite migration was added.

#### Main issues and final fixes

- Readiness uses an explicit `status="ok"` JSON contract; readiness timeout remains 60 seconds with the existing 1–300 second process-level policy.
- `analysis_option_detail` uses a provider-neutral 2048-token stage budget; other stage budgets, temperature, reasoning policy, and repair limits are unchanged.
- Provider narration DTOs remain strict and separate from persisted compatibility DTOs; semantic safeguards stay in the application layer.
- The final llama.cpp qualification used 16K context for the `governed_access` representative scenario. This is the qualified runtime configuration for that scenario, not a claim about every model or endpoint.

#### Final acceptance evidence

- The final dual UAT ran exactly once without retry, in the order `llama_cpp → remote NVIDIA endpoint`; both full `governed_access` workflows passed readiness, discovery, analysis, and report.
- Both endpoints used JSON Schema with `fallback_used=false`. Each produced `option_count=3`; analysis used 1024 tokens for A0 and 2048 tokens for each option detail, while report Part A/B used 2048 tokens. All successful executor attempts were first-pass; report semantic pass was `[1]`; deterministic fallback was not invoked.
- Normalized deterministic results were equal: `matching_status=matched`, `no_case_reason=null`, `recommendation_category=rules_first`, `decision_authority=human_final_decision`, `processing_boundary=private_endpoint`; reviewed cases were unique (`case-08`, `case-09`, `case-10`). Required phases and gates remained unchanged: `HG-01 blocked`, `HG-03 assistive_only`, `HG-05 requires_controls`, `HG-06 requires_controls`.
- Duplicate/read-only, reload/history/download, restart, persistence, and secret-safety checks passed for both endpoints. Automatic approval, direct permission write, unapproved external PII processing, and high-risk autonomous provisioning remained disallowed.
- Sanitized compatibility evidence is retained outside the repository without prompts, facts, provider content, reasoning, request payloads, or secrets. P7.2a checkpoint passed; the overall P7.2 initiative is not complete.

#### P7.2b next boundary

- The next checkpoint is the four-scenario golden compatibility matrix across the same provider-independent deterministic boundaries. Keep `P7.2b` Pending until that matrix is independently qualified.

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

### P8.1a Portfolio baseline — Complete

- README 說明產品定位、使用者、AI／deterministic boundary、啟動方式與目前狀態；
- 提供五分鐘 UAT runtime、model-profile readiness 與 synthetic `governed_access` Demo runbook；
- 新增作品集 brief，包含架構圖、workflow 圖、P7.2a 脫敏 evidence、截圖清單、技術亮點與 limitations；
- 明確保留 P7.2b Pending、P7.2 overall incomplete 與 P8.1b Pending；
- 不修改 application behavior、provider implementation、deterministic logic、database schema 或 dependencies；本 checkpoint 的文件與 portfolio brief 已完成。

Acceptance checkpoint：

- 新使用者可依 README 建立 `.venv`、啟動 UAT、建立並測試 model profile，並依 runbook 展示 synthetic `governed_access`；
- portfolio brief 不包含 API key、Authorization、prompt、provider raw response、reasoning 或真實員工資料；
- P7.2a、P7.2b、P7.2 overall 與 P8.1b 狀態互相一致；
- 文件 diff 通過 `git diff --check`，且不引入 production code、migration、dependency 或 CI workflow 變更。
- 明確記錄目前 UI 不提供 profile import／export，API key 的明文 local profile storage limitation，以及只支援 Bearer authentication 的 capability scope。

### P8.1b-1 Traditional Chinese UI wording and product guidance — Complete

- 完成模型設定、能力選擇、模型可用性測試與 API key 清除語意的繁體中文產品引導；
- 完成 blocked-no-provider、Discovery、Assessment、Results、history 與 download 的使用者文案整理；
- 保留安全錯誤與 fail-closed 語意，不顯示 raw provider response、secret 或內部例外；
- 補上 UI helper、能力標籤與 Streamlit smoke 測試；
- 未修改 API、provider、deterministic decision、SQLite schema、migration、dependency 或 CI。

Acceptance checkpoint：

- offline UI tests、完整測試、Ruff 與 format check 通過；
- capability wire values 與 API key preserve／clear payload 語意不變；
- P7.2b 仍 Pending，P7.2 overall 仍 incomplete。

### P8.1b-2 Product-owner and release acceptance — Pending

- Review Traditional Chinese wording and business usefulness；
- Verify blocked-no-provider behavior and project-bound model selection；
- Verify Discovery、Assessment、Results、reload、history 與 download；
- Review P7.2 compatibility evidence；
- Complete release-readiness acceptance and decide whether to start P7.2b。
- Current acceptance blockers include stale SQLite runtime readiness and a combined model-settings long page; the bounded fix separates runtime preflight, profile create/edit IA, and minimal project brief input.
- Re-acceptance must verify fresh schema v8, actionable database failure guidance, profile preservation, and the unchanged provider/deterministic boundaries.
- Subsequent manual UAT also found cross-round interview widget-state leakage and an assessment validation exception escaping as generic `internal_error`; the bounded fix scopes widget keys by project/version/round/question, enforces mutually exclusive answer states, and returns safe fail-closed `analysis_result_invalid` without partial persistence.
- Independent review additionally found illegal callbacks on widgets inside the Streamlit form. The follow-up uses one mutually exclusive answer-status radio plus a scoped text area, with no input-widget callbacks; AppTest covers real rendering and round/project isolation. A temporary-SQLite API test covers safe failure, no partial analysis, preserved interview data, and successful retry after valid fake output.

P8.1b overall remains Pending until P8.1b-2 is accepted。

### Renewed manual UAT follow-up — Pending

- Allow an initial missing/unknown brief fact to be asked once with its canonical key; an already-asked gap remains closed.
- Preserve interview answers as superseding fact revisions with visible answer references; confirmed facts still require explicit correction.
- Enforce a deterministic first-round material-gap policy and bounded semantic retry when the provider incorrectly claims `interview_complete=true`.
- Keep confirmation success persisted before round generation; generation failure stays retryable from `READY_FOR_INTERVIEW` with safe UI guidance.

- Stop re-asking unknown/missing interview topics and keep the second round only for confirmed material decision gaps。
- Combine the explicit frontend action into analysis followed by report, while preserving separate persisted analysis/report states and retry behavior。
- Keep implementation references solution-scoped, omit empty reviewed-case sections, and distinguish the pre-scale roadmap review。
- P8.1b-2 remains Pending; P7.2b remains Pending and P7.2 overall remains incomplete。
- Renewed UAT follow-up also requires nullable new-project widget state to render safely and UAT browser errors to hide local traceback details without changing provider, deterministic, persistence, or schema behavior。

## Deferred

- Consumer installer and release packaging.
- Automatic llama.cpp or model installation.
- Multi-agent, LangGraph, FAISS and Docker.
- Cloud deployment, accounts, online search and multi-tenancy.
- Production-grade credential encryption.
- PDF／DOCX export.
