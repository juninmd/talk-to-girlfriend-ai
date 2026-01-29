import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import schedule


@pytest.fixture
def mock_client():
    with patch("backend.tools.schedule.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_schedule_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.send_message = AsyncMock()

    result = await schedule.schedule_message(
        chat_id=123, message="Test", minutes_from_now=10
    )
    assert "Message scheduled" in result


@pytest.mark.asyncio
async def test_schedule_message_validation(mock_client):
    result = await schedule.schedule_message(
        chat_id=123, message="Test", minutes_from_now=0
    )
    assert "must be at least 1" in result

    result = await schedule.schedule_message(
        chat_id=123, message="Test", minutes_from_now=1000000
    )
    assert "cannot exceed" in result
