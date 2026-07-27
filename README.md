# AI PoC Planner

AI PoC Planner 的目标是成为一个本机运行、连接真实 OpenAI-compatible 模型的企业 AI 导入需求分析与 PoC 规划工具。它将协助使用者厘清流程、资料、治理条件与可行方案，并输出可执行的 Markdown 规划报告。

## 当前状态：规格重置中

`main` 目前是技术基础，不是可用产品，也不是发布版本。它包含 FastAPI、SQLite、LangChain 与 Streamlit 的实验性基础，但当前公开流程使用 scripted fake provider，不能真正理解使用者输入，也不能代表可行 MVP。

PR #8 保留为技术原型与实验记录，不作为发布版本。真实模型连接、可行 MVP 的访谈与报告已经具备后端契约；产品 UI 目前只完成首页、项目历史与模型设定，完整流程与启动体验仍未完成。

fake provider 仅用于自动测试；它不是可提供给使用者的分析模式。项目不会自动回退到 fake model。

## 新 viable MVP 方向

第一版会优先支持使用者自行启动的 llama.cpp OpenAI-compatible server，并允许在产品中新增、编辑、删除、测试与切换多个本机模型连接。配置包含 profile name、base URL、model name 与可空 API key；第一版存放于 ignored 本机 JSON 文件。

没有已测试且选定的真实模型连接时，产品必须拒绝正式 AI 分析，而不是产生 scripted 结果。

后续产品流程为：

```text
最小初始需求 → AI 需求理解 → 使用者确认／纠正 → 最多三轮针对性访谈
→ 结构化确认事实 → AI／非 AI／混合分析 → hard gates → 正式 Markdown 报告
```

完整契约与实施顺序请参阅：

- [产品规格](docs/spec/SPEC.md)
- [实施计划](docs/spec/PLAN.md)
- [任务拆分](docs/spec/TASKS.md)
- [项目记录](PROJECT_LOG.md)

## 保留的技术资产

- Python、FastAPI、Streamlit 与 Pydantic contracts
- SQLite 本机持久化基础
- LangChain 单一 Agent/typed-tool 实验边界
- 六维评分、加权总分与 hard-gate 规则资产
- 九类 AI opportunity catalog 与三个非 AI 方向
- pytest、Ruff 与 deterministic fake-provider 测试设施

这些资产需要依照新规格重新验证，不能据此宣称 real-provider 产品已完成。

## 明确不包含

第一版不包含多 Agent、LangGraph、FAISS、Docker、云端部署、用户账号、Email 登录、自动下载模型、安装或管理 llama.cpp、React/Next.js、PDF/DOCX、在线案例搜索、多租户或生产级凭证加密。

本项目也不负责安装 llama.cpp 或下载 GGUF 模型。

## 开发状态与命令

现有命令仅供技术基础与自动测试维护使用，并非面向终端使用者的产品安装说明：

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

未来会规划 `安装 AI PoC Planner.bat`、`启动 AI PoC Planner.bat` 与 `停止 AI PoC Planner.bat`。在这些入口完成前，不应把手动建立环境、手动分别启动 FastAPI/Streamlit，或 fake demo 当作产品使用方式。

## 安全与资料边界

- API key 不会提交到仓库；第一版本机 profile JSON 必须被忽略。
- 高影响领域只能提供辅助建议，保留人工最终决定。
- 未授权资料外传、禁止外部端点、缺少必要人工审核等 hard-gate 冲突会阻挡结论。
- 产品只保存正式可见的使用者/AI 对话与结构化事实；不保存 system prompt、chain of thought、LangChain tool trajectory 或 raw provider metadata。

## Phase 1 provider foundation

Phase 1 implements local model-profile storage, an OpenAI-compatible chat
adapter, safe profile/status API endpoints, a formal-analysis readiness guard,
and an opt-in llama.cpp validation. This is a provider foundation only: the
Streamlit product UI has not been rebuilt, and the formal business interview,
scoring, and report are not connected to a real model yet.

Profiles are stored for this MVP in a private local JSON file. The default is
`%LOCALAPPDATA%\AI-PoC-Planner\model_profiles.json` on Windows, or
`~/.local/share/ai-poc-planner/model_profiles.json` elsewhere; set
`AI_POC_PLANNER_DATA_DIR` to override the directory. API keys are plaintext in
that user-local file by deliberate MVP trade-off. They are excluded from public
profile responses, normal representations, and safe error responses.

The user starts llama.cpp independently. The default test suite never calls the
network. To opt in after starting an OpenAI-compatible llama.cpp server, set
`AI_POC_PLANNER_LLAMA_CPP_TEST=1`,
`AI_POC_PLANNER_LLAMA_CPP_BASE_URL`, and
`AI_POC_PLANNER_LLAMA_CPP_MODEL`; `AI_POC_PLANNER_LLAMA_CPP_API_KEY` is optional.
Then run:

```powershell
python -m pytest tests/providers/test_llama_cpp_integration.py
```

### Qwen3 compatibility note

In the verified Qwen3 llama.cpp UAT, the server's default reasoning mode
returned only a reasoning channel while ordinary assistant `content` was empty.
The Phase 1 adapter requires non-empty assistant content for a successful
connection test, so that UAT server used `--reasoning off`. This is a verified
startup configuration for that model/server combination, not a requirement for
every model. The current adapter does not treat reasoning-only responses as
successful connection-test responses.

A successful connection test proves only that the configured endpoint was
reachable at that time. Fake providers remain offline automated-test fixtures;
there is no fake runtime fallback for provider readiness or formal analysis.

## Phase 2 durable project history

Phase 2 adds durable SQLite project identity and linear planning-version
history. Creating a project creates version 1 in `draft`; completing a version
makes it immutable, and subsequent edits require a new successor version. A
successor copies only visible conversation and current fact revisions, with new
local IDs and mapped message references.

Only user-visible conversation is persisted. Facts are append-only revisions:
an assistant assumption needs visible evidence, a user confirmation creates a
new confirmed revision, and changing a confirmed fact requires an explicit
user correction. The database does not persist system prompts, reasoning,
chain-of-thought, tool/LangChain trajectories, raw provider metadata, API keys,
or Authorization headers.

## Phase 3 real-model discovery interview

Phase 3 adds a provider-readiness-gated minimal initial brief, a real-model
requirement-understanding confirmation/correction step, and a contextual
interview bounded to three rounds with at most three questions per round.
Only visible conversation and append-only fact revisions survive reload. A
completed version remains immutable; Phase 3 stops at `ready_for_assessment`.

The structured provider boundary accepts only a complete JSON object (or one
complete `json` fence), validates it with Pydantic, and allows one safe repair
retry. It never persists system prompts, reasoning, chain of thought, tool
trajectories, raw provider responses, API keys, or Authorization headers.
Runtime calls require the currently selected, enabled, successfully tested real
profile to match the version's safe model snapshot. Test fakes are dependency
injection only; no fake runtime fallback exists.

The real Qwen3 llama.cpp UAT passed with `--reasoning off`, including correction
and regeneration, confirmation, bounded interview completion, and fresh-app
reload. Provider connection status remains process-local and is not persisted.
## Phase 4 evidence-backed assessment

Phase 4 adds one immutable assessment for an assessment-ready project version.
The real selected/tested profile proposes two to four AI, non-AI,
foundations-first, or hybrid options and six evidence-backed ratings. The
application resolves only current `Fxxx` fact tokens, assigns the normative
weights, calculates the total deterministically, and evaluates the existing
hard gates. Option generation is staged: the provider selects an option index,
then receives a kind-specific option-detail schema; the application derives the
formal conclusion from that selected kind. The provider cannot submit a formal
conclusion, weights, totals, rule results, or a gate disposition.

SQLite schema v6 persists normalized analysis results and one immutable,
fact-backed Markdown planning report per assessed version. P5.2 generates the
eighteen report narration fields in two staged real-provider calls (Report Part
A and Report Part B), then deterministically renders program-owned conclusions,
scores, gates, resolved fact references, and reviewed-case attribution. Numeric
claims and KPI thresholds are rejected unless fact-backed. It does not persist
prompts, reasoning, raw provider responses, API keys, Authorization headers, or
base URLs. A report completes its version. Phase 6.1 adds a Streamlit home,
project-history, and model-settings surface that talks only to the existing
FastAPI HTTP API. Phase 6.2 adds the Phase 3 brief, real-provider requirement
understanding, correction/confirmation, and bounded interview flow through the
same public HTTP boundary. It restores durable discovery state after a rerun,
shows only readable facts at completion, and keeps UUIDs, raw JSON, prompts,
API URLs, SQLite paths, and technical diagnostics out of the UI. A real NVIDIA
NIM browser UAT covered profile readiness, brief, correction, confirmation,
unknown answer, proactive fact addition, bounded completion, and refresh
 recovery. Phase 6.3 adds readable Phase 4 assessment and Phase 5 report views:
 it follows the persisted version status, renders the six scores, hard gates,
 options, risks, gaps, all eighteen report sections, and saved reviewed-case
 sources through FastAPI HTTP only. It downloads the persisted UTF-8 Markdown
 without re-rendering it, restores the latest result-capable project after a
 refresh, and keeps fact tokens, UUIDs, raw JSON, API URLs, SQLite paths, and
 technical diagnostics out of the UI. A real NVIDIA browser UAT covered
 assessment creation, Report Part A/Part B, completed-state refresh, and
 Markdown download. Phase 6.4 closes out the Discovery experience with natural-
language correction, free supplementary input, bounded material questions,
human-readable summaries, and explicit Traditional Chinese output. The product
now enters work through four global pages only: Home, New project, Project
history, and Model settings. Discovery, assessment, and reports are rendered
inside the selected project's workspace. New-project routing remains stable on
refresh; the selected model profile is persisted safely with the project, and
copying a project prefills only its initial brief. P6.5 assessment redesign has
not started.

The real NVIDIA NIM `openai/gpt-oss-20b` UAT passed twice through the production
API using `json_schema`, `reasoning_effort=low`, and temporary local state. The
test covers Phase 3 discovery through immutable Phase 4 assessment, duplicate
blocking, and fresh-app reload. Provider reasoning channels and raw responses
are ignored and never persisted.

P5.2 also passed a report-only NVIDIA UAT twice using two fresh temporary
states. Each run uses production assessed-version repositories, calls Report
Part A and Report Part B, persists an immutable report, completes the version,
and verifies GET, duplicate POST blocking, and fresh-app reload. Full
cross-phase report UAT is deferred to Phase 8.

## Reviewed local cases

Phase 5.1 provides a small, manually reviewed local case library in
`data/reviewed_cases.json`. It is read-only, source-backed, Pydantic-validated,
and matched deterministically by exact opportunity type, applicability tags,
evidence grade, and stable case ID. It does not use online search, embeddings,
FAISS, a provider, or case-derived scoring. Phase 5.2 adds a strict structured
report draft, deterministic Markdown rendering, immutable reloadable storage,
and report APIs; it does not add a Streamlit product UI.

## Windows local runtime

P7.1 provides a one-command, supervised local runtime for browser UAT. From
the project directory run:

```powershell
.\scripts\start-local.ps1 -Mode Uat
```

The launcher requires this project's `.venv\Scripts\python.exe`; it never
falls back to a system Python. It starts FastAPI and Streamlit, selects free
ports in API `18610-18699` and UI `18501-18599`, validates API identity, opens
the browser, and stops both child processes together on Ctrl+C or child failure.
It does not use port 8000 as a product default.

Persistent data is separate in `%LOCALAPPDATA%\AI-PoC-Planner` (Local) and
`%LOCALAPPDATA%\AI-PoC-Planner-UAT` (Uat): SQLite, profile storage, safe state,
and logs. Profiles/selection persist, while readiness intentionally returns to
untested after a process restart. API keys retain the existing local plaintext
MVP trade-off and are not written to launcher state or logs. This is not an
installer, Windows auto-start, or release package.

```powershell
.\scripts\status-local.ps1 -Mode Uat
.\scripts\stop-local.ps1 -Mode Uat
```

## License

MIT License. See [LICENSE](LICENSE).
