from __future__ import annotations

from ai_poc_planner.application.discovery_interview import DiscoveryInterviewService


def test_discovery_provider_prompts_require_traditional_chinese() -> None:
    understanding = DiscoveryInterviewService._understanding_messages([])[0]["content"]
    interview = DiscoveryInterviewService._round_messages([], [], 2)[0]["content"]

    assert "Traditional Chinese" in understanding
    assert "Traditional Chinese" in interview
    assert "do not translate JSON keys" in understanding
    assert "one round" in interview


def test_understanding_prompt_requires_full_user_confirmation_content() -> None:
    prompt = DiscoveryInterviewService._understanding_messages([])[0]["content"]

    assert "four to six complete Markdown bullet points" in prompt
    assert "current workflow and main problem" in prompt
    assert "desired outcome" in prompt
    assert "responsibility boundary" in prompt
    assert "human decision or approval boundary" in prompt
    assert "systems/data/deployment constraints" in prompt
    assert "whether AI is necessary" in prompt


def test_interview_prompt_limits_questions_to_material_decisions() -> None:
    prompt = DiscoveryInterviewService._round_messages([], [], 2)[0]["content"]

    assert "hard gate" in prompt
    assert "human-review boundary" in prompt
    assert "precise percentages or budgets" in prompt
    assert "deterministic reviewed-case matching" in prompt
    assert "gap analysis" in prompt
    assert "Do not keep asking merely to fill facts" in prompt


def test_interview_prompt_carries_safe_question_history_and_closes_gaps() -> None:
    messages = DiscoveryInterviewService._round_messages([], [], 1)
    prompt = " ".join(str(message["content"]) for message in messages)

    assert "previous_questions" in prompt
    assert "Unknown or missing" in prompt
    assert "clarification_round_*" in prompt
