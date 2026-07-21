"""Small argparse CLI for the deterministic offline demonstration."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ai_poc_planner.agent.demo import run_scripted_planning_demo
from ai_poc_planner.agent.planning import PlanningAgentExecutionError
from ai_poc_planner.application.demo import build_demo_request
from ai_poc_planner.application.report import ReportExportError
from ai_poc_planner.application.workflow import PlanningError, run_offline_planning


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ai_poc_planner")
    subcommands = parser.add_subparsers(dest="command")
    demo = subcommands.add_parser("demo", help="run the deterministic offline demo")
    demo.add_argument(
        "--output",
        default="artifacts/demo-report.md",
        help="Markdown report path (default: artifacts/demo-report.md)",
    )
    subcommands.add_parser(
        "planning-demo",
        help="run the scripted offline LangChain planning demonstration",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    if arguments.command is None:
        parser.print_help()
        return 0
    if arguments.command == "planning-demo":
        try:
            result = run_scripted_planning_demo()
        except PlanningAgentExecutionError as error:
            print(f"error [{error.code}]", file=sys.stderr)
            return 2
        print(f"Planning status: {result.status}")
        print(
            "Opportunity candidates: "
            + ", ".join(
                candidate.opportunity_type.value
                for candidate in result.opportunity_match.candidates
            )
        )
        return 0
    try:
        result = run_offline_planning(build_demo_request(output_path=arguments.output))
    except (PlanningError, ReportExportError) as error:
        print(f"error [{error.code}]: {error}", file=sys.stderr)
        return 2

    print(f"Project: {result.project.title}")
    print(f"Weighted score: {result.assessment.weighted_score}")
    print(f"Gate disposition: {result.assessment.gate_disposition.value}")
    print(f"Recommendation: {result.assessment.recommendation.value}")
    print(f"Report: {result.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
