import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import chat


@pytest.fixture
def mock_client():
    with patch("backend.tools.chat.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_chats(mock_client):
    mock_dialog = MagicMock()
    mock_dialog.entity.id = 123
    mock_dialog.entity.title = "Test Chat"
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])

    result = await chat.get_chats()
    assert "Test Chat" in result


@pytest.mark.asyncio
async def test_list_chats(mock_client):
    from telethon.tl.types import User

    mock_dialog = MagicMock()
    mock_dialog.entity = MagicMock(spec=User)
    mock_dialog.entity.id = 123
    mock_dialog.entity.first_name = "User1"
    mock_dialog.entity.last_name = None
    mock_dialog.entity.username = None
    mock_dialog.unread_count = 0
    mock_dialog.dialog.unread_mark = False

    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])

    result = await chat.list_chats()
    assert "User1" in result

    # Test filtering
    result = await chat.list_chats(chat_type="user")
    assert "User1" in result

    result = await chat.list_chats(chat_type="group")
    assert "No chats found" in result


@pytest.mark.asyncio
async def test_get_chat(mock_client):
    from telethon.tl.types import User

    mock_user = MagicMock(spec=User)
    mock_user.id = 123
    mock_user.first_name = "Test"
    mock_user.last_name = None
    mock_user.username = None
    mock_user.phone = None
    mock_user.bot = False
    mock_user.verified = False
    mock_client.get_entity = AsyncMock(return_value=mock_user)

    result = await chat.get_chat(chat_id=123)
    assert "Test" in result


@pytest.mark.asyncio
async def test_leave_chat(mock_client):
    from telethon.tl.types import Channel

    mock_channel = MagicMock(spec=Channel)
    mock_channel.id = 123
    mock_channel.title = "Channel"
    mock_client.get_entity = AsyncMock(return_value=mock_channel)
    mock_client.side_effect = AsyncMock()

    result = await chat.leave_chat(chat_id=123)
    assert "Left channel" in result


@pytest.mark.asyncio
async def test_create_group(mock_client):
    mock_client.get_entity = AsyncMock(return_value="user_obj")
    mock_result = MagicMock()
    mock_result.chats = [MagicMock(id=999)]
    mock_client.side_effect = AsyncMock(
        return_value=mock_result
    )  # for call to client()

    result = await chat.create_group("New Group", [123])
    assert "Group created" in result
