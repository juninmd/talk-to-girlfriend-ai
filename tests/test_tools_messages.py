import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import messages


@pytest.fixture
def mock_client():
    with patch("backend.tools.messages.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_messages(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)

    mock_msg = MagicMock()
    mock_msg.id = 1
    mock_msg.message = "Hello"
    mock_msg.date = "2024-01-01"
    # Ensure attributes for get_sender_name are set
    mock_msg.sender.first_name = "Sender"
    mock_msg.sender.last_name = None
    mock_msg.sender.title = None  # Explicitly None if using getattr check order
    del mock_msg.sender.title  # or delete to force first_name usage

    mock_msg.reply_to = None

    mock_client.get_messages = AsyncMock(return_value=[mock_msg])

    result = await messages.get_messages(chat_id=123)
    assert "Hello" in result
    assert "Sender" in result


@pytest.mark.asyncio
async def test_send_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.send_message = AsyncMock()

    result = await messages.send_message(chat_id=123, message="Hi")
    assert "sent successfully" in result
    mock_client.send_message.assert_called_with(mock_entity, "Hi")


@pytest.mark.asyncio
async def test_list_messages(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)

    mock_msg = MagicMock()
    mock_msg.id = 2
    mock_msg.message = "Search Result"
    # Ensure sender attributes
    del mock_msg.sender.title
    mock_msg.sender.first_name = "Sender"
    mock_msg.sender.last_name = None

    mock_client.get_messages = AsyncMock(return_value=[mock_msg])

    result = await messages.list_messages(chat_id=123, search_query="Result")
    assert "Search Result" in result


@pytest.mark.asyncio
async def test_reply_to_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.send_message = AsyncMock()

    result = await messages.reply_to_message(chat_id=123, message_id=1, text="Reply")
    assert "Replied to message" in result
    mock_client.send_message.assert_called_with(mock_entity, "Reply", reply_to=1)


@pytest.mark.asyncio
async def test_delete_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.delete_messages = AsyncMock()

    result = await messages.delete_message(chat_id=123, message_id=1)
    assert "deleted" in result


@pytest.mark.asyncio
async def test_pin_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.pin_message = AsyncMock()

    result = await messages.pin_message(chat_id=123, message_id=1)
    assert "pinned" in result


@pytest.mark.asyncio
async def test_unpin_message(mock_client):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.unpin_message = AsyncMock()

    result = await messages.unpin_message(chat_id=123, message_id=1)
    assert "unpinned" in result
