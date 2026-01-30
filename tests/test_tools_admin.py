import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import admin


@pytest.fixture
def mock_client():
    with patch("backend.tools.admin.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_promote_admin(mock_client):
    mock_chat = MagicMock()
    mock_chat.title = "Test Group"
    mock_user = MagicMock()
    mock_user.id = 456

    mock_client.get_entity = AsyncMock(side_effect=[mock_chat, mock_user])

    # Mock return of client call (EditAdminRequest)
    mock_client.side_effect = AsyncMock()

    result = await admin.promote_admin(group_id=123, user_id=456)
    assert "Successfully promoted" in result


@pytest.mark.asyncio
async def test_demote_admin(mock_client):
    mock_chat = MagicMock()
    mock_user = MagicMock()
    mock_client.get_entity = AsyncMock(side_effect=[mock_chat, mock_user])
    mock_client.side_effect = AsyncMock()

    result = await admin.demote_admin(group_id=123, user_id=456)
    assert "Successfully demoted" in result


@pytest.mark.asyncio
async def test_ban_user(mock_client):
    mock_chat = MagicMock()
    mock_chat.title = "Test Group"
    mock_user = MagicMock()
    mock_client.get_entity = AsyncMock(side_effect=[mock_chat, mock_user])
    mock_client.side_effect = AsyncMock()

    result = await admin.ban_user(chat_id=123, user_id=456)
    assert "banned from chat" in result


@pytest.mark.asyncio
async def test_unban_user(mock_client):
    mock_chat = MagicMock()
    mock_user = MagicMock()
    mock_client.get_entity = AsyncMock(side_effect=[mock_chat, mock_user])
    mock_client.side_effect = AsyncMock()

    result = await admin.unban_user(chat_id=123, user_id=456)
    assert "unbanned" in result


@pytest.mark.asyncio
async def test_get_admins(mock_client):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.first_name = "Admin"
    mock_user.last_name = None
    mock_client.get_participants = AsyncMock(return_value=[mock_user])

    result = await admin.get_admins(chat_id=123)
    assert "Admin" in result


@pytest.mark.asyncio
async def test_get_banned_users(mock_client):
    mock_user = MagicMock()
    mock_user.id = 2
    mock_user.first_name = "Banned"
    mock_user.last_name = None
    mock_client.get_participants = AsyncMock(return_value=[mock_user])

    result = await admin.get_banned_users(chat_id=123)
    assert "Banned" in result


@pytest.mark.asyncio
async def test_get_recent_actions(mock_client):
    mock_result = MagicMock()
    mock_event = MagicMock()
    mock_event.to_dict.return_value = {"action": "delete"}
    mock_result.events = [mock_event]
    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await admin.get_recent_actions(chat_id=123)
    assert "delete" in result


@pytest.mark.asyncio
async def test_get_recent_actions_empty(mock_client):
    mock_result = MagicMock()
    mock_result.events = []
    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await admin.get_recent_actions(chat_id=123)
    assert "No recent admin actions found" in result
