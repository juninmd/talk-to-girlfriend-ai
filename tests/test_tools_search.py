import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import search

@pytest.fixture
def mock_client():
    with patch("backend.tools.search.client") as mock:
        yield mock

@pytest.mark.asyncio
async def test_search_public_chats(mock_client):
    from telethon.tl.types import User
    mock_result = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = 123
    mock_user.first_name = "User"
    mock_user.last_name = None
    mock_user.username = None
    mock_user.phone = None

    mock_result.users = [mock_user]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await search.search_public_chats("test")
    assert "123" in result

@pytest.mark.asyncio
async def test_resolve_username(mock_client):
    mock_result = MagicMock()
    mock_result.__str__.return_value = "ResolvedUser"

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await search.resolve_username("test")
    assert "ResolvedUser" in result
