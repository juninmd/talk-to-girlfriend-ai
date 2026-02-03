import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.conversation import conversation_service
from telethon.tl.types import User


@pytest.mark.asyncio
async def test_handle_private_message():
    # Setup
    event = MagicMock()
    event.is_private = True
    event.message.out = False
    event.message.message = "Hello"
    event.chat_id = 123
    event.sender = User(id=456, bot=False)

    # Mock _generate_and_send_reply
    original_method = conversation_service._generate_and_send_reply
    conversation_service._generate_and_send_reply = AsyncMock()

    try:
        await conversation_service.handle_incoming_message(event)

        conversation_service._generate_and_send_reply.assert_called_once()
        # Verify reply_to_msg_id is None for private
        _, kwargs = conversation_service._generate_and_send_reply.call_args
        assert kwargs.get("reply_to_msg_id") is None
    finally:
        conversation_service._generate_and_send_reply = original_method


@pytest.mark.asyncio
async def test_handle_group_message_no_mention():
    event = MagicMock()
    event.is_private = False
    event.message.mentioned = False
    event.message.out = False
    event.message.message = "Hello Group"
    event.sender = User(id=456, bot=False)

    original_method = conversation_service._generate_and_send_reply
    conversation_service._generate_and_send_reply = AsyncMock()

    try:
        await conversation_service.handle_incoming_message(event)

        conversation_service._generate_and_send_reply.assert_not_called()
    finally:
        conversation_service._generate_and_send_reply = original_method


@pytest.mark.asyncio
async def test_handle_group_message_with_mention():
    event = MagicMock()
    event.is_private = False
    event.message.mentioned = True
    event.message.out = False
    event.message.message = "Hello Bot"
    event.chat_id = 999
    event.message.id = 555
    event.sender = User(id=456, bot=False)

    original_method = conversation_service._generate_and_send_reply
    conversation_service._generate_and_send_reply = AsyncMock()

    try:
        await conversation_service.handle_incoming_message(event)

        conversation_service._generate_and_send_reply.assert_called_once()
        # Verify reply_to_msg_id is the message id for group
        _, kwargs = conversation_service._generate_and_send_reply.call_args
        assert kwargs.get("reply_to_msg_id") == 555
    finally:
        conversation_service._generate_and_send_reply = original_method
