"""Deterministic Markdown rendering and local file export."""

from __future__ import annotations

import html
import json
from pathlib import Path

from ai_poc_planner.domain.models import (
    AnalysisProject,
    EvidenceReference,
    JSONValue,
    PocProposal,
)
from ai_poc_planner.domain.workflow import Assessment

REPORT_SECTIONS = (
    "# AI PoC Planning Report",
    "## Executive Summary",
    "## Project Context",
    "## Interview Summary",
    "## Assessment Scorecard",
    "## Hard Gates and Required Controls",
    "## Recommendation",
    "## Proposed PoC Scope",
    "## Architecture",
    "## Data Requirements",
    "## Human Review and Governance",
    "## KPIs",
    "## Risks and Assumptions",
    "## Similar Cases",
    "## Evidence",
    "## Next Steps",
)
_SENSITIVE_KEY_MARKERS = (
    "api_key",
    "token",
    "password",
    "secret",
    "cookie",
    "private_key",
    "authorization",
)


class ReportExportError(OSError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _line(value: object) -> str:
    escaped = html.escape(
        str(value).replace("\r", " ").replace("\n", " ").strip(),
        quote=True,
    ).replace("\\", "\\\\")
    for marker in ("`", "*", "_", "[", "]", "(", ")", "#", "!"):
        escaped = escaped.replace(marker, f"\\{marker}")
    return escaped


def _table(value: object) -> str:
    return _line(value).replace("|", "\\|")


def _bullets(values: list[str], *, empty: str = "None") -> list[str]:
    return [f"- {_line(value)}" for value in values] or [f"- {empty}"]


def _redact_json(value: JSONValue) -> JSONValue:
    if isinstance(value, dict):
        return {
            key: (
                "[REDACTED]"
                if any(marker in key.lower() for marker in _SENSITIVE_KEY_MARKERS)
                else _redact_json(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json(item) for item in value]
    return value


def _interview_lines(values: dict[str, JSONValue]) -> list[str]:
    redacted = _redact_json(values)
    assert isinstance(redacted, dict)
    return [
        f"- **{_line(key)}:** {_line(json.dumps(value, ensure_ascii=False))}"
        for key, value in sorted(redacted.items())
    ]


def render_markdown_report(
    *,
    project: AnalysisProject,
    interview_answers: dict[str, JSONValue],
    assessment: Assessment,
    proposal: PocProposal,
    evidence: list[EvidenceReference],
) -> str:
    """Render one stable report solely from validated typed domain objects."""
    lines = [REPORT_SECTIONS[0], "", REPORT_SECTIONS[1], ""]
    lines.extend(
        [
            _line(proposal.executive_summary),
            "",
            REPORT_SECTIONS[2],
            "",
            f"- **Project:** {_line(project.title)}",
            f"- **Problem:** {_line(project.problem_statement)}",
            f"- **Project ID:** `{project.id}`",
            "",
            REPORT_SECTIONS[3],
            "",
            *_interview_lines(interview_answers),
            "",
            REPORT_SECTIONS[4],
            "",
            "| Dimension | Rating | Weight | Points | Rule／Rationale | Evidence |",
            "|---|---:|---:|---:|---|---|",
        ]
    )
    lines.extend(
        "| "
        + " | ".join(
            (
                _table(score.dimension.value),
                str(score.rating),
                f"{score.weight}%",
                f"{score.weighted_points:.2f}",
                _table(score.rationale),
                _table(", ".join(score.evidence_refs) or "None"),
            )
        )
        + " |"
        for score in assessment.scores
    )
    lines.extend(
        [
            "",
            f"**Weighted score:** {assessment.weighted_score}/100",
            "",
            REPORT_SECTIONS[5],
            "",
            f"**Aggregate disposition:** `{assessment.gate_disposition.value}`",
        ]
    )
    if assessment.hard_gates:
        for gate in assessment.hard_gates:
            lines.extend(
                [
                    "",
                    f"### {_line(gate.rule_id)} — {gate.disposition.value}",
                    "",
                    _line(gate.reason),
                    "",
                    *_bullets(gate.required_controls, empty="No additional controls"),
                    "",
                    "Evidence: " + ", ".join(_line(ref) for ref in gate.evidence_refs),
                ]
            )
    else:
        lines.extend(["", "No hard gates triggered under rule version 1.0."])

    lines.extend(
        [
            "",
            REPORT_SECTIONS[6],
            "",
            f"**{assessment.recommendation.value}** — {_line(assessment.rationale)}",
            "",
            REPORT_SECTIONS[7],
            "",
            f"**Boundary:** {_line(proposal.suggested_use_case_boundary)}",
            "",
            "### In scope",
            "",
            *_bullets(proposal.in_scope),
            "",
            "### Out of scope",
            "",
            *_bullets(proposal.out_of_scope),
            "",
            "### Milestones",
            "",
            *_bullets(proposal.poc_milestones),
            "",
            f"**Estimated duration:** {proposal.estimated_weeks} weeks",
            "",
            "**Estimated team:** "
            + ", ".join(_line(item) for item in proposal.estimated_team),
            "",
            REPORT_SECTIONS[8],
            "",
        ]
    )
    if proposal.architecture_options:
        for option in proposal.architecture_options:
            lines.extend(
                [
                    f"### {_line(option.name)}",
                    "",
                    _line(option.summary),
                    "",
                    *_bullets(option.components),
                    "",
                ]
            )
    else:
        lines.extend(
            ["Architecture planning is paused until redesign is approved.", ""]
        )

    controls = [
        control for gate in assessment.hard_gates for control in gate.required_controls
    ]
    lines.extend(
        [
            REPORT_SECTIONS[9],
            "",
            *_bullets(proposal.required_data),
            "",
            REPORT_SECTIONS[10],
            "",
            *_bullets([*proposal.human_review_points, *controls]),
            "",
            REPORT_SECTIONS[11],
            "",
            *_bullets(proposal.success_metrics),
            "",
            REPORT_SECTIONS[12],
            "",
            "### Risks",
            "",
            *_bullets(proposal.risks),
            "",
            "### Assumptions",
            "",
            *_bullets([*proposal.roi_assumptions, *proposal.scope_assumptions]),
            "",
            REPORT_SECTIONS[13],
            "",
        ]
    )
    for case in proposal.similar_cases:
        lines.append(
            f"- **{_line(case.title)}** (`{_line(case.case_id)}`, "
            f"fixture score {case.similarity:.2f}) — {_line(case.fit_summary)}; "
            f"source `{_line(case.source_ref)}`"
        )
    if not proposal.similar_cases:
        lines.append("- None")
    lines.extend(["", REPORT_SECTIONS[14], ""])
    lines.extend(
        f"- `{item.id}` — {_line(item.label)}; source `{_line(item.source_ref)}`"
        for item in evidence
    )
    lines.extend(
        [
            "",
            "Rule IDs: "
            + (
                ", ".join(_line(gate.rule_id) for gate in assessment.hard_gates)
                or "None"
            ),
            "",
            REPORT_SECTIONS[15],
            "",
            *_bullets(proposal.next_actions),
            "",
        ]
    )
    return "\n".join(lines).rstrip()


def write_markdown_report(markdown: str, output_path: str | Path) -> str:
    path = Path(output_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    except OSError as error:
        raise ReportExportError(
            "report_write_failed", f"unable to write Markdown report: {path}"
        ) from error
    return str(path.resolve())
