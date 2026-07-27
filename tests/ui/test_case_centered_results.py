from __future__ import annotations

from ai_poc_planner.ui.results import case_centered_overview


def test_results_presentation_prioritizes_cases_without_internal_identifiers() -> None:
    view = case_centered_overview(
        {
            "case_centered": {
                "matching_status": "matched",
                "recommendation_title": "權限申請標準化與人工審核輔助",
                "recommendation_basis": ["有來源案例支持"],
                "matched_cases": [
                    {
                        "case": {
                            "case_id": "case-01",
                            "title": "權限申請審核案例",
                            "organization": "Example",
                            "source_references": [
                                {"label": "官方來源", "url": "https://example.test"}
                            ],
                        },
                        "reference_value": {
                            "level": "high",
                            "score": 88,
                            "basis": ["案例已通過審核"],
                            "unknown_items": ["缺少近期成果證據"],
                        },
                        "project_fit": {
                            "level": "medium",
                            "score": 64,
                            "similarities": ["都保留人工核准"],
                            "key_differences": ["系統依賴不同"],
                            "needs_confirmation": ["需要確認角色目錄"],
                        },
                        "gaps": {
                            "ready_conditions": ["有主管責任"],
                            "missing_conditions": ["缺少追蹤狀態"],
                            "not_directly_transferable": ["不可自主開通"],
                            "needs_confirmation": ["需要確認資料邊界"],
                        },
                    }
                ],
                "transferable_practices": [
                    {
                        "name": "權限范本標準化",
                        "source_case_ids": ["case-01"],
                        "source_case_titles": ["權限申請審核案例"],
                        "case_evidence": "案例記錄主管審核。",
                        "transferable_part": "先從職位范本選擇。",
                        "required_adjustments": ["保留人工核准"],
                        "current_stage": "第一階段 PoC",
                        "prerequisites": ["角色目錄"],
                        "not_applicable_scope": ["自主開通"],
                    }
                ],
                "gate_impacts": [
                    {
                        "rule_id": "HG-01",
                        "disposition": "blocked",
                        "affected_stage": "第一階段 PoC",
                        "limits": ["不自動核准"],
                        "does_not_limit": ["人工輔助仍可進行"],
                        "release_conditions": ["完成治理審查"],
                    }
                ],
                "phased_path": [
                    {
                        "phase_name": "第一階段 PoC",
                        "description": "人工覆核",
                        "actions": ["建立測試資料"],
                        "inputs": ["脫敏資料"],
                        "outputs": ["覆核紀錄"],
                        "users": ["主管"],
                        "human_decision_boundary": "人工最終決策",
                        "not_doing": ["不自主核准"],
                        "source_case_ids": ["case-01"],
                        "remaining_gaps": ["角色目錄"],
                        "gate_impacts": ["HG-01"],
                        "acceptance_criteria": ["完成覆核紀錄"],
                    }
                ],
            }
        }
    )
    text = repr(view)
    assert view["cases"][0]["title"] == "權限申請審核案例"
    assert view["practices"][0]["source_case_titles"] == ["權限申請審核案例"]
    assert "case-01" not in text
    assert "HG-01" not in text
    assert "autonomous_action" not in text


def test_results_presentation_localizes_case_tags_and_gate_controls() -> None:
    view = case_centered_overview(
        {
            "case_centered": {
                "matching_status": "matched",
                "recommendation_title": "人工輔助路線",
                "matched_cases": [
                    {
                        "case": {
                            "title": "案例",
                            "organization": "組織",
                            "source_references": [],
                        },
                        "reference_value": {},
                        "project_fit": {},
                        "gaps": {
                            "not_directly_transferable": [
                                "案例標示的限制：autonomous_action"
                            ]
                        },
                    }
                ],
                "gate_impacts": [
                    {
                        "disposition": "blocked",
                        "affected_stage": "第一階段 PoC",
                        "limits": [],
                        "does_not_limit": [],
                        "release_conditions": [
                            "obtain documented authorization and lawful basis"
                        ],
                    }
                ],
            }
        }
    )

    text = repr(view)
    assert "autonomous_action" not in text
    assert "不得自主執行高風險動作" in text
    assert "取得書面授權與合法依據" in text
