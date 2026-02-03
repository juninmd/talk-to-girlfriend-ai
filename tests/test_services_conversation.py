import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.conversation import ConversationService
from telethon.tl.types import User


@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def service(mock_client):
    service = ConversationService()
    service.client = mock_client
    return service


@pytest.mark.asyncio
async def test_handle_incoming_message_trigger(service):
    event = MagicMock()
    event.message.out = False
    event.is_private = True
    event.message.message = "Hello"
    event.sender = MagicMock(spec=User)
    event.sender.bot = False
    event.sender.first_name = "TestUser"
    event.message.sender = event.sender
    event.chat_id = 123

    # We patch the method on the instance `service`
    with patch.object(service, "_generate_and_send_reply", new_callable=AsyncMock) as mock_reply:
        await service.handle_incoming_message(event)
        # Since it uses asyncio.create_task, we just check if it was called.
        # But wait, create_task schedules it. We need to ensure the task is created.
        # Ideally we should mock create_task or just check if the coroutine was created?
        # Actually, since we mock `_generate_and_send_reply` as AsyncMock, calling it returns a coroutine.
        # create_task(coro) will consume it.
        # But `mock_reply` will record the call.
        mock_reply.assert_called_once_with(123, "Hello", "TestUser", reply_to_msg_id=None)


@pytest.mark.asyncio
async def test_handle_incoming_message_ignore_outgoing(service):
    event = MagicMock()
    event.message.out = True  # Outgoing
    event.is_private = True
    event.message.message = "Hello"

    with patch.object(service, "_generate_and_send_reply", new_callable=AsyncMock) as mock_reply:
        await service.handle_incoming_message(event)
        mock_reply.assert_not_called()


@pytest.mark.asyncio
async def test_handle_incoming_message_ignore_bot(service):
    event = MagicMock()
    event.message.out = False
    event.is_private = True
    event.message.message = "Hello"
    event.sender = MagicMock(spec=User)
    event.sender.bot = True  # Bot

    with patch.object(service, "_generate_and_send_reply", new_callable=AsyncMock) as mock_reply:
        await service.handle_incoming_message(event)
        mock_reply.assert_not_called()


@pytest.mark.asyncio
async def test_generate_and_send_reply(service):
    chat_id = 123
    user_message = "Hi"

    # Mock AI Service
    with patch("backend.services.conversation.ai_service") as mock_ai:
        mock_ai.generate_natural_response = AsyncMock(return_value="Hello there")

        # Mock client context manager for 'typing'
        # client.action(chat_id, "typing") returns an async context manager
        action_cm = AsyncMock()
        service.client.action.return_value = action_cm
        service.client.send_message = AsyncMock()

        # We need to speed up sleep for tests or patch it
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await service._generate_and_send_reply(chat_id, user_message, "TestUser")

        mock_ai.generate_natural_response.assert_called_once_with(
            chat_id, user_message, "TestUser"
        )
        service.client.send_message.assert_called_once_with(chat_id, "Hello there", reply_to=None)
