import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Add backend to path if needed, or rely on python -m pytest
from backend.services.ai import AIService


class MockFact:
    def __init__(self, id, category, created_at):
        self.id = id
        self.category = category
        self.created_at = created_at
        self.entity = "Ent"
        self.value = "Val"
        self.chat_id = 1
        self.sender_id = 1


@pytest.fixture
def mock_session_cls():
    with patch("backend.services.ai.Session") as mock:
        yield mock


@pytest.fixture
def mock_engine():
    with patch("backend.services.ai.engine") as mock:
        yield mock


def create_fact(id, category, days_ago):
    return MockFact(id=id, category=category, created_at=datetime.now() - timedelta(days=days_ago))


def test_get_context_prioritization(mock_session_cls, mock_engine):
    # Setup Service
    service = AIService()

    # Setup mock facts
    # 5 Personal (Tier 1) - Old (10 days ago)
    personal_facts = [create_fact(i, "pessoal", 10) for i in range(1, 6)]
    # 30 Tech (Tier 2) - Medium (5 days ago)
    tech_facts = [create_fact(i, "tech", 5) for i in range(6, 36)]
    # 30 General (Tier 3) - New (1 day ago)
    general_facts = [create_fact(i, "general", 1) for i in range(36, 66)]

    # Mock DB Session
    mock_db_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_db_session

    # Prepare Result objects for each call
    res_history = MagicMock()
    res_history.all.return_value = []

    res_tier1 = MagicMock()
    res_tier1.all.return_value = personal_facts  # Returns 5

    res_tier2 = MagicMock()
    # The DB query would limit to 20, so we simulate that
    res_tier2.all.return_value = tech_facts[:20]

    res_tier3 = MagicMock()
    # Logic: 50 - 5 (pessoal) - 20 (tech) = 25 slots left.
    # The DB query would limit to 25.
    res_tier3.all.return_value = general_facts[:25]

    mock_db_session.exec.side_effect = [res_history, res_tier1, res_tier2, res_tier3]

    # Act
    history, facts = service._get_context(chat_id=1, sender_id=1)

    # Assert
    assert len(facts) == 50

    # Verify Composition
    pessoal_count = sum(1 for f in facts if f.category == "pessoal")
    tech_count = sum(1 for f in facts if f.category == "tech")
    general_count = sum(1 for f in facts if f.category == "general")

    assert pessoal_count == 5
    assert tech_count == 20
    assert general_count == 25

    # Verify Sorting (Newest First)
    # General (1 day ago) should be first
    # Tech (5 days ago)
    # Personal (10 days ago)
    assert facts[0].category == "general"
    assert facts[-1].category == "pessoal"
