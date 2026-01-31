import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import chat


@pytest.fixture
def mock_client():
    with patch("backend.tools.chat.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_mute_chat(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()  # client()

    res = await chat.mute_chat(123)
    assert "muted" in res


@pytest.mark.asyncio
async def test_unmute_chat(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    res = await chat.unmute_chat(123)
    assert "unmuted" in res


@pytest.mark.asyncio
async def test_archive_chat(mock_client):
    mock_client.get_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    res = await chat.archive_chat(123)
    assert "archived" in res


@pytest.mark.asyncio
async def test_unarchive_chat(mock_client):
    mock_client.get_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    res = await chat.unarchive_chat(123)
    assert "unarchived" in res


@pytest.mark.asyncio
async def test_edit_chat_title(mock_client):
    from telethon.tl.types import Chat, Channel

    # Channel
    c = MagicMock(spec=Channel)
    mock_client.get_entity = AsyncMock(return_value=c)
    mock_client.side_effect = AsyncMock()
    res = await chat.edit_chat_title(123, "New Title")
    assert "updated" in res

    # Chat
    c = MagicMock(spec=Chat)
    mock_client.get_entity = AsyncMock(return_value=c)
    res = await chat.edit_chat_title(123, "New Title")
    assert "updated" in res

    # Invalid
    mock_client.get_entity = AsyncMock(return_value="User")
    res = await chat.edit_chat_title(123, "New Title")
    assert "Cannot edit title" in res


@pytest.mark.asyncio
async def test_edit_chat_photo(mock_client):
    from telethon.tl.types import Chat

    c = MagicMock(spec=Chat)
    mock_client.get_entity = AsyncMock(return_value=c)
    mock_client.upload_file = AsyncMock(return_value="file")
    mock_client.side_effect = AsyncMock()

    res = await chat.edit_chat_photo(123, "photo.jpg")
    assert "updated" in res


@pytest.mark.asyncio
async def test_delete_chat_photo(mock_client):
    from telethon.tl.types import Channel

    c = MagicMock(spec=Channel)
    mock_client.get_entity = AsyncMock(return_value=c)
    mock_client.side_effect = AsyncMock()

    res = await chat.delete_chat_photo(123)
    assert "deleted" in res


@pytest.mark.asyncio
async def test_get_invite_link(mock_client):
    mock_client.get_entity = AsyncMock(return_value="peer")
    # First try (ExportChatInviteRequest) fails
    # Second try (export_chat_invite_link) succeeds

    # Mocking client() call to raise
    mock_client.side_effect = Exception("RPCError")

    mock_client.export_chat_invite_link = AsyncMock(return_value="https://t.me/invite")

    res = await chat.get_invite_link(123)
    assert "https://t.me/invite" in res


@pytest.mark.asyncio
async def test_join_chat_by_link(mock_client):
    mock_res = MagicMock()
    mock_chat = MagicMock()
    mock_chat.title = "JoinedChat"
    mock_res.chats = [mock_chat]

    mock_client.side_effect = AsyncMock(return_value=mock_res)

    res = await chat.join_chat_by_link("https://t.me/+hash")
    assert "JoinedChat" in res

    # Direct hash
    res = await chat.join_chat_by_link("hash")
    assert "JoinedChat" in res
