import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.services.telegram import TelegramService, format_entity, format_message
from telethon.tl.types import User, Chat, Channel


def test_format_entity():
    user = MagicMock(spec=User)
    user.id = 1
    user.first_name = "A"
    user.last_name = "B"
    user.username = "a"
    user.phone = "123"

    res = format_entity(user)
    assert res["id"] == 1
    assert res["type"] == "user"
    assert res["first_name"] == "A"

    chat = MagicMock(spec=Chat)
    chat.id = 2
    chat.title = "Group"

    res = format_entity(chat)
    assert res["id"] == 2
    assert res["type"] == "chat"

    channel = MagicMock(spec=Channel)
    channel.id = 3
    channel.title = "Channel"
    channel.username = "c"

    res = format_entity(channel)
    assert res["id"] == 3
    assert res["type"] == "channel"


def test_format_message():
    msg = MagicMock()
    msg.id = 1
    msg.date.isoformat.return_value = "2024-01-01"
    msg.message = "Hi"
    msg.out = True
    msg.sender.first_name = "Sender"
    msg.sender.last_name = None
    msg.sender.id = 123
    msg.reply_to.reply_to_msg_id = 99
    msg.media = None

    res = format_message(msg)
    assert res["id"] == 1
    assert res["text"] == "Hi"
    assert res["sender_name"] == "Sender"
    assert res["reply_to_msg_id"] == 99
    assert res["has_media"] is False


@pytest.fixture
def mock_client():
    with patch("backend.services.telegram.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_telegram_service_methods(mock_client):
    # get_me
    user_me = MagicMock(spec=User)
    user_me.id = 1
    mock_client.get_me = AsyncMock(return_value=user_me)
    res = await TelegramService.get_me()
    assert res["id"] == 1

    # get_chats
    mock_dialog = MagicMock()
    user_dialog = MagicMock(spec=User)
    user_dialog.id = 2
    mock_dialog.entity = user_dialog
    mock_client.get_dialogs = AsyncMock(return_value=[mock_dialog])
    res = await TelegramService.get_chats(limit=10)
    assert len(res["chats"]) == 1

    # get_chat
    user_chat = MagicMock(spec=User)
    user_chat.id = 3
    mock_client.get_entity = AsyncMock(return_value=user_chat)
    res = await TelegramService.get_chat(chat_id=3)
    assert res["id"] == 3

    # get_messages
    mock_msg = MagicMock()
    mock_msg.id = 1
    mock_client.get_messages = AsyncMock(return_value=[mock_msg])
    res = await TelegramService.get_messages(chat_id=3, limit=10)
    assert len(res["messages"]) == 1

    # send_message
    mock_sent = MagicMock()
    mock_sent.id = 2
    mock_client.send_message = AsyncMock(return_value=mock_sent)
    from backend.api.models import SendMessageRequest

    res = await TelegramService.send_message(3, SendMessageRequest(message="Hi"))
    assert res["message_id"] == 2

    # send_file
    mock_client.send_file = AsyncMock(return_value=mock_sent)
    res = await TelegramService.send_file(3, b"content", "test.txt", None, False)
    assert res["message_id"] == 2

    # get_contacts
    mock_result = MagicMock()
    user_contact = MagicMock(spec=User)
    user_contact.id = 4
    mock_result.users = [user_contact]
    mock_client.side_effect = AsyncMock(return_value=mock_result)  # for __call__
    res = await TelegramService.get_contacts()
    assert len(res["contacts"]) == 1

    # send_reaction
    # reset side effect if needed, but here it's fine
    from backend.api.models import ReactionRequest

    res = await TelegramService.send_reaction(3, 1, ReactionRequest(emoji="👍"))
    assert res["success"] is True
