import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import drafts


@pytest.fixture
def mock_client():
    with patch("backend.tools.drafts.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_save_draft(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()  # for client call

    result = await drafts.save_draft(chat_id=123, message="Draft")
    assert "Draft saved" in result


@pytest.mark.asyncio
async def test_get_drafts(mock_client):
    mock_result = MagicMock()
    mock_update = MagicMock()
    # Ensure attributes are serializable or handled
    mock_update.draft.message = "Draft Message"
    mock_update.draft.date.isoformat.return_value = "2024-01-01"
    mock_update.draft.no_webpage = False
    mock_update.peer.user_id = 123
    mock_result.updates = [mock_update]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await drafts.get_drafts()
    assert "Draft Message" in result
    assert "123" in result


@pytest.mark.asyncio
async def test_clear_draft(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    result = await drafts.clear_draft(chat_id=123)
    assert "Draft cleared" in result
