# Project Log

## Current goal

Draft PR #24 is refining the Results report's reader-facing information hierarchy. P7.2 provider compatibility and local inference has not started.

## Results Narrative and Comparison Redesign

- `ReportSynthesis` 2.2 puts a complete deterministic recommendation article before the concise interview table and the integrated option, case, and project-gap comparison.
- Mature cases are evidence for a candidate direction rather than an independent ranking; current/target/gap rows are the second table in that same comparison chapter.
- Raw interview questions, evidence lists, internal fact tokens, and standalone next steps are removed from the reader-facing report. The collapsible technical appendix retains only Chinese six-dimension scores and hard-limit details without identifiers.
- The same persisted `ReportSynthesis` is used by the Results UI and Markdown renderer; Streamlit continues to access report data through the FastAPI boundary.
- SQLite `solution_patterns`, `reviewed_cases`, and their explicit solution/case/reference relations are now the runtime source of truth. Provider titles, translations, case facts, outcomes, and source URLs cannot enter the formal report.
- Deterministic matching now requires the approved solution-key relation before fit/gap ranking; report creation fail-closes when the project route, stored solution, or stored case facts disagree.
- The permission-request route requires confirmed access-request, fixed-rule, and human-approval signals together. It formally recommends `權限申請標準化、規則檢查與人工審批`, with manager final approval, IT provisioning, and no automatic approval or direct permission-system write in phase one.
- A follow-up owner investigation found that the earlier governed-access UAT still inserted an unrelated knowledge-retrieval comparison row despite its no-case fallback, and then exposed generic interview/no-case labels. Governed reports now restrict comparison rows to relevant baselines, do not use other-domain cases as evidence, map approval and audit questions to readable topics, and use application-format completeness, rule-prompt correctness, manager approval time, and exception-record completeness as the visible acceptance measures.
- The earlier artifacts remain preserved and were not reused or overwritten. The fresh populated UAT is `artifacts/results-catalog-consistency-uat-20260729-134851-final-clean/`; it uses a new persistent state root, schema `8`, `ReportSynthesis` `2.2`, three approved matching cases, and three persisted interview findings. API first/refresh/history downloads are byte-identical; UI first/history downloads are byte-identical and line-for-line identical to the API report.
- Final verification passed: `622 passed, 6 skipped`, Ruff, format check, and `git diff --check`.

## Current status

- PR #20 (P6.4), PR #21 (P7.1), and PR #22 (P6.5) are merged into `main`.
- PR #23 contains four Traditional Chinese golden scenarios, deterministic recommendation categories, regression coverage, and NVIDIA-compatible headed Chrome UAT.
- The verified baseline is `601 passed, 6 skipped`, plus Ruff, formatting, diff checks, and GitHub Actions.
- P6.6 technical acceptance passed. The product owner's final wording and business-usefulness review was not completed on the final version and is deferred to P8.1; it is not claimed as passed.
- Known follow-ups are provider narrative fallback behavior, six opt-in live-provider tests, and insufficient reviewed-case coverage.
- No P7.2 Ollama, LM Studio, vLLM, local-model installation, or multi-provider adapter work has started.

## P6.6 acceptance baseline

- Four synthetic scenarios cover AI-assisted knowledge retrieval, rules-first expense checks, governed access requests, and readiness-first predictive maintenance.
- Formal categories are derived from confirmed facts and deterministic gates rather than provider option labels.
- Golden invariants cover opportunities, recommendation category, gaps, phases, forbidden conclusions, human boundaries, deployment constraints, case traceability, and idempotency.
- Headed Chrome UAT covered project creation, model readiness, understanding/correction, interview, assessment, report, refresh, history re-entry, and duplicate-run protection.
- Provider narrative fallback and case-library limitations are recorded in `docs/uat/P6_6_PRODUCT_ACCEPTANCE.md`.

## Historical phase records

以下內容保留各階段當時的決策與驗收脈絡，不代表目前分支、`main` 或 PR 狀態。

- PR #8 passed automated validation but failed manual product UAT because a scripted fake-model vertical slice was incorrectly treated as product success.
- The reset adopted a local-first, real-provider-first architecture using Python, FastAPI, Streamlit, SQLite, Pydantic, pytest, and Ruff.
- Phase 1 delivered model profiles, an OpenAI-compatible adapter, readiness/status APIs, and opt-in llama.cpp integration. Real Qwen3 llama.cpp UAT passed on a loopback-only endpoint.
- Phase 2 delivered immutable project versions, visible conversation, append-only fact revisions, and additive SQLite migration.
- Phase 3 delivered structured requirement understanding, correction, and a bounded contextual interview without storing prompts, raw responses, or reasoning traces.
- Phase 4 delivered structured options, program-owned weighted scoring, and deterministic HG-01 through HG-07 enforcement. NVIDIA-compatible UAT passed.
- Phase 5 delivered nine reviewed source-backed cases and an immutable Markdown report with numeric-claim safeguards.
- Phase 6.1–P6.3 delivered the HTTP-only Streamlit product surface for home/history/settings, Discovery, assessment, and persisted reports.
- P6.4 established project-centred navigation and durable model binding.
- P6.5 made reviewed cases, fit, gaps, transferable practices, gates, and phased implementation the primary Results flow.
- P7.1 delivered the project-owned Windows start/status/stop runtime, dynamic ports, identity checks, and Local/Uat isolation.

## Decisions retained

- LangChain remains an optional single-agent integration boundary; no multi-agent or LangGraph work is authorised.
- Fake providers remain deterministic test infrastructure only.
- Deterministic matching, formal recommendation categories, weighted scoring, and hard gates remain program-owned.
- Reviewed cases require explicit sources and may not fabricate companies, metrics, or outcomes.

## Decisions revoked

- A fake-model vertical slice is not viable-MVP acceptance.
- A public scripted fake mode is not a substitute for a real provider.
- Provider output does not own formal scores, recommendation constraints, or hard gates.
- FAISS, Docker, cloud deployment, or provider compatibility must not be described as complete without evidence.

## Next sequence

1. Merge the P6.6 technical baseline.
2. Implement P7.2 provider compatibility and local inference against one local OpenAI-compatible endpoint first.
3. Reuse the four P6.6 golden scenarios for the provider compatibility matrix.
4. Complete P8.1 product-owner and portfolio UAT, including the final decision on whether six-dimension scores remain visible or secondary.

## Deferred

- Consumer installer and release packaging.
- Automatic llama.cpp or model installation.
- Multi-agent, LangGraph, FAISS, Docker, cloud deployment, accounts, online search, and multi-tenancy.
- Production-grade credential encryption and PDF/DOCX export.
