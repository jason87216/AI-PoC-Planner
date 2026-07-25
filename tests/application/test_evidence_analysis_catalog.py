from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_poc_planner.domain.enums import FactStatus
from ai_poc_planner.domain.project_history import FactRevision


def test_analysis_fact_catalog_order_uses_public_fact_key_contract() -> None:
    """Phase 4 must not depend on persistence-only projection fields."""

    facts = [
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key=" Zeta ",
            value="x",
            status=FactStatus.CONFIRMED,
            reference_message_ids=[uuid4()],
            created_at=datetime.now(UTC),
        ),
        FactRevision(
            id=uuid4(),
            version_id=uuid4(),
            fact_key="alpha",
            value="x",
            status=FactStatus.CONFIRMED,
            reference_message_ids=[uuid4()],
            created_at=datetime.now(UTC),
        ),
    ]

    ordered = sorted(facts, key=lambda item: item.fact_key.strip().casefold())

    assert [item.fact_key for item in ordered] == ["alpha", "Zeta"]
