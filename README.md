# AI PoC Planner

AI PoC Planner 的目标是成为一个本机运行、连接真实 OpenAI-compatible 模型的企业 AI 导入需求分析与 PoC 规划工具。它将协助使用者厘清流程、资料、治理条件与可行方案，并输出可执行的 Markdown 规划报告。

## 当前状态：规格重置中

`main` 目前是技术基础，不是可用产品，也不是发布版本。它包含 FastAPI、SQLite、LangChain 与 Streamlit 的实验性基础，但当前公开流程使用 scripted fake provider，不能真正理解使用者输入，也不能代表可行 MVP。

PR #8 保留为技术原型与实验记录，不作为发布版本。真实模型连接、可行 MVP 的访谈、报告、产品 UI 与启动体验均尚未实现。

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

Phase 3 real-model interviews are not implemented yet. Scoring, hard-gate
rewrites, reports, and the Streamlit product UI are also still outside the
implemented product flow.

## License

MIT License. See [LICENSE](LICENSE).
