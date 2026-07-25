from __future__ import annotations

from ai_poc_planner.application.discovery_interview import DiscoveryInterviewService


def test_discovery_provider_prompts_require_traditional_chinese() -> None:
    understanding = DiscoveryInterviewService._understanding_messages([])[0]["content"]
    interview = DiscoveryInterviewService._round_messages([], [], 2)[0]["content"]

    assert "Traditional Chinese" in understanding
    assert "Traditional Chinese" in interview
    assert "do not translate JSON keys" in understanding
    assert "one round" in interview


def test_interview_prompt_limits_questions_to_material_decisions() -> None:
    prompt = DiscoveryInterviewService._round_messages([], [], 2)[0]["content"]

    assert "hard gate" in prompt
    assert "human-review boundary" in prompt
    assert "precise percentages or budgets" in prompt
