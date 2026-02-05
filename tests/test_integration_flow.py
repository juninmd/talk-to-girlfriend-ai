import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from telethon.tl.types import User
from backend.services.conversation import conversation_service
from backend.services.reporting import reporting_service
from backend.services.ai import ai_service
from backend.settings import settings


@pytest.mark.asyncio
async def test_conversation_flow_reply():
    """
    Test that an incoming message triggers a reply with correct context.
    """
    # Override settings to avoid delays
    settings.CONVERSATION_MIN_DELAY = 0.0
    settings.CONVERSATION_MAX_DELAY = 0.0
    settings.CONVERSATION_TYPING_SPEED = 0.0

    # Mock Event
    mock_event = MagicMock()
    mock_event.chat_id = 12345
    mock_event.sender_id = 98765
    mock_event.message.message = "Hello bot, how are you?"
    mock_event.message.id = 100
    mock_event.message.out = False
    mock_event.is_private = True
    mock_event.message.mentioned = False

    # Mock Sender
    mock_sender = User(id=98765, first_name="Test", last_name="User", username="testuser")
    mock_event.sender = mock_sender
    mock_event.message.sender = mock_sender

    # Mock Client actions
    mock_client = AsyncMock()

    # FIX: client.action should be a sync method returning an async context manager
    mock_client.action = MagicMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = None
    mock_context.__aexit__.return_value = None
    mock_client.action.return_value = mock_context

    # Inject mock client
    conversation_service.client = mock_client

    # Mock AI Service response
    with patch.object(ai_service, "generate_natural_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "I am fine, thanks!"

        # Act: Handle message
        await conversation_service.handle_incoming_message(mock_event)

        # Wait for the async task created inside to complete
        await asyncio.sleep(0.1)

        # Assert AI was called correctly
        mock_gen.assert_called_once()
        args, _ = mock_gen.call_args
        assert args[0] == 12345  # chat_id
        assert args[1] == "Hello bot, how are you?"  # message
        assert args[2] == "Test User"  # sender_name

        # Assert Reply was sent
        mock_client.send_message.assert_called_once()
        call_args = mock_client.send_message.call_args
        assert call_args[0][0] == 12345
        assert call_args[0][1] == "I am fine, thanks!"


@pytest.mark.asyncio
async def test_reporting_flow():
    """
    Test report generation and sending logic.
    """
    # Mock settings
    settings.REPORT_CHANNEL_ID = -100123456789

    # Mock messages fetch (simulating DB return)
    mock_date = MagicMock()
    mock_date.strftime.return_value = "10:00"

    mock_msgs = [
        MagicMock(chat_id=1, text="Hi", sender_name="User1", date=mock_date),
        MagicMock(chat_id=1, text="Hello", sender_name="User2", date=mock_date),
    ]

    # Mock Client for Entity Resolution
    mock_client = AsyncMock()
    mock_channel = MagicMock()
    mock_channel.id = -100123456789
    mock_channel.title = "Report Channel"
    mock_client.get_entity.return_value = mock_channel

    reporting_service.client = mock_client

    # Mock methods
    with patch.object(reporting_service, "_fetch_messages_for_report", return_value=mock_msgs):
        with patch.object(
            ai_service, "summarize_conversations", new_callable=AsyncMock
        ) as mock_sum:
            mock_sum.return_value = "Here is the summary."

            # Act
            report = await reporting_service.generate_daily_report()

            # Assert
            assert "Here is the summary" in report
            assert "# 📅 Relatório Diário" in report
            assert "Conversas Ativas:** 1" in report

            # Verify sending to channel
            mock_client.get_entity.assert_any_call(-100123456789)

            mock_client.send_message.assert_called_once()
            args, _ = mock_client.send_message.call_args
            assert args[0].id == -100123456789
            assert args[1] == report


@pytest.mark.asyncio
async def test_reporting_flow_fallback():
    """
    Test report generation fallback when no channel ID is set.
    """
    # Mock settings to None
    settings.REPORT_CHANNEL_ID = None

    mock_msgs = [MagicMock(chat_id=1, text="Hi", sender_name="User1", date=MagicMock())]

    mock_client = AsyncMock()
    mock_me = MagicMock()
    mock_me.id = 111
    mock_client.get_me.return_value = mock_me

    reporting_service.client = mock_client

    with patch.object(reporting_service, "_fetch_messages_for_report", return_value=mock_msgs):
        with patch.object(
            ai_service, "summarize_conversations", new_callable=AsyncMock
        ) as mock_sum:
            mock_sum.return_value = "Summary"

            # Act
            await reporting_service.generate_daily_report()

            # Verify get_me was called (fallback resolution)
            mock_client.get_me.assert_called()

            # Verify send_message called to 'me'
            mock_client.send_message.assert_called()
            args, _ = mock_client.send_message.call_args
            assert args[0].id == 111
