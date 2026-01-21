import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import polls

@pytest.fixture
def mock_client():
    with patch("backend.tools.polls.client") as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_poll(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.side_effect = AsyncMock()

    result = await polls.create_poll(chat_id=123, question="Q?", options=["A", "B"])
    assert "Poll created successfully" in result

@pytest.mark.asyncio
async def test_create_poll_validation(mock_client):
    # Mock client.get_entity even for validation tests if they reach that point, or mock to fail
    mock_client.get_entity = AsyncMock(return_value=MagicMock())

    result = await polls.create_poll(chat_id=123, question="Q?", options=["A"])
    assert "at least 2 options" in result

    result = await polls.create_poll(chat_id=123, question="Q?", options=["A"]*11)
    assert "at most 10 options" in result

    result = await polls.create_poll(chat_id=123, question="Q?", options=["A", "B"], close_date="invalid")
    assert "Invalid close_date format" in result
