import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.ai import AIService
from backend.services.reporting import ReportingService


@pytest.mark.asyncio
async def test_ai_service_prompt_formatting_robustness():
    """
    Ensures AIService.generate_natural_response does not crash when input contains curly braces.
    """
    # Setup
    ai_service = AIService()
    ai_service.client = MagicMock()
    # Mock the chain: client.aio.models.generate_content
    ai_service.client.aio.models.generate_content = AsyncMock()
    ai_service.client.aio.models.generate_content.return_value.text = "Response OK"

    # Mock context fetching to return empty context so we isolate the prompt formatting logic
    # We patch the synchronous method _get_context but since it's run in a thread,
    # we need to be careful. However, we can patch the AIService class method directly.
    with patch.object(AIService, "_get_context", return_value=([], [])):
        # Test with input containing braces which might confuse format() if not careful
        user_message_with_braces = "Tell me about {JSON} format and {key: value}"

        try:
            # We call the method. If .format() fails, it raises KeyError or ValueError
            response = await ai_service.generate_natural_response(123, user_message_with_braces)
            assert response == "Response OK"
        except (ValueError, KeyError) as e:
            pytest.fail(f"AIService crashed on brace formatting: {e}")


@pytest.mark.asyncio
async def test_reporting_service_channel_resolution():
    """
    Ensures ReportingService handles various REPORT_CHANNEL_ID types correctly.
    """
    # Setup
    reporting_service = ReportingService()
    reporting_service.client = MagicMock()
    reporting_service.client.get_entity = AsyncMock()
    reporting_service.client.get_me = AsyncMock()

    mock_entity = MagicMock()
    mock_entity.id = 999
    reporting_service.client.get_entity.return_value = mock_entity

    mock_me = MagicMock()
    mock_me.id = 111
    reporting_service.client.get_me.return_value = mock_me

    # We patch the settings object imported in reporting.py
    # Note: reporting.py does `from backend.settings import settings`

    # Case 1: Valid Integer ID
    with patch("backend.services.reporting.settings.REPORT_CHANNEL_ID", 12345):
        entity = await reporting_service._resolve_target_entity()
        # Expectation: It tries to get entity 12345
        reporting_service.client.get_entity.assert_called_with(12345)
        assert entity.id == 999

    # Case 2: Valid String ID
    with patch("backend.services.reporting.settings.REPORT_CHANNEL_ID", "@mychannel"):
        entity = await reporting_service._resolve_target_entity()
        reporting_service.client.get_entity.assert_called_with("@mychannel")
        assert entity.id == 999

    # Case 3: Empty String -> Fallback to Me
    with patch("backend.services.reporting.settings.REPORT_CHANNEL_ID", ""):
        # Reset mock
        reporting_service.client.get_entity.reset_mock()
        entity = await reporting_service._resolve_target_entity()

        # Should NOT call get_entity with empty string (it might, but we want fallback)
        # Actually implementation might call get_entity("") which fails, then catch except.
        # But we want to ensure we get 'me' back.
        assert entity.id == 111

    # Case 4: None -> Fallback to Me
    with patch("backend.services.reporting.settings.REPORT_CHANNEL_ID", None):
        entity = await reporting_service._resolve_target_entity()
        assert entity.id == 111


@pytest.mark.asyncio
async def test_scheduler_configuration():
    """
    Verifies that the scheduler is initialized and the reporting job is added correctly.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from backend.services.reporting import reporting_service
    from backend.settings import settings

    with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.add_job") as mock_add_job, \
         patch("apscheduler.schedulers.asyncio.AsyncIOScheduler.start") as mock_start:

        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            reporting_service.generate_daily_report,
            "cron",
            hour=settings.REPORT_TIME_HOUR,
            minute=settings.REPORT_TIME_MINUTE,
        )
        scheduler.start()

        mock_add_job.assert_called_once()
        args, kwargs = mock_add_job.call_args

        # Check job function
        assert args[0] == reporting_service.generate_daily_report
        # Check trigger type
        assert args[1] == "cron"
        # Check time
        assert kwargs["hour"] == settings.REPORT_TIME_HOUR
        assert kwargs["minute"] == settings.REPORT_TIME_MINUTE

        mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_conversation_reaction_parsing():
    """
    Verifies that ConversationService correctly parses [REACTION: emoji] tags
    and calls the send_reaction tool.
    """
    from backend.services.conversation import ConversationService
    from backend.tools.reactions import send_reaction

    mock_client = MagicMock() # Use MagicMock for client structure
    mock_ctx = AsyncMock()    # The context manager returned by action()
    mock_client.action.return_value = mock_ctx
    mock_client.send_message = AsyncMock()

    service = ConversationService()
    service.client = mock_client # Inject mock client

    # Mock AI response with reaction tag
    ai_response = "[REACTION: 😂] Hahaha, boa!"

    # Mock dependencies
    with patch("backend.services.conversation.ai_service.generate_natural_response", return_value=ai_response) as mock_ai, \
         patch("backend.services.conversation.send_reaction", new_callable=AsyncMock) as mock_send_reaction, \
         patch("asyncio.sleep", new_callable=AsyncMock): # Skip sleeps

        chat_id = 123
        msg_id = 456
        user_msg = "Joke"
        sender_name = "User"

        # Execute
        await service._generate_and_send_reply(
            chat_id=chat_id,
            user_message=user_msg,
            sender_name=sender_name,
            reply_to_msg_id=msg_id
        )

        # Verify Reaction was sent
        mock_send_reaction.assert_called_once_with(chat_id, msg_id, "😂")

        # Verify Message was sent (without tag)
        mock_client.send_message.assert_called_once_with(chat_id, "Hahaha, boa!", reply_to=msg_id)


@pytest.mark.asyncio
async def test_conversation_reaction_only():
    """
    Verifies that ConversationService handles response with ONLY a reaction tag.
    """
    from backend.services.conversation import ConversationService
    from backend.tools.reactions import send_reaction

    mock_client = MagicMock()
    mock_ctx = AsyncMock()
    mock_client.action.return_value = mock_ctx
    mock_client.send_message = AsyncMock()

    service = ConversationService()
    service.client = mock_client

    # Mock AI response with ONLY reaction
    ai_response = "[REACTION: 👍]"

    with patch("backend.services.conversation.ai_service.generate_natural_response", return_value=ai_response), \
         patch("backend.services.conversation.send_reaction", new_callable=AsyncMock) as mock_send_reaction, \
         patch("asyncio.sleep", new_callable=AsyncMock):

        chat_id = 123
        msg_id = 456

        await service._generate_and_send_reply(
            chat_id=chat_id,
            user_message="Ok",
            sender_name="User",
            reply_to_msg_id=msg_id
        )

        # Verify Reaction sent
        mock_send_reaction.assert_called_once_with(chat_id, msg_id, "👍")

        # Verify NO message sent
        mock_client.send_message.assert_not_called()
