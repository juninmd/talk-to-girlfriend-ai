import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.learning import LearningService
from backend.services.reporting import ReportingService
from backend.services.ai import AIService

# --- Learning Service Tests ---


@pytest.mark.asyncio
async def test_learning_service_ingest_history_batch_processing():
    # Mock dependencies
    mock_client = AsyncMock()

    # Create 10 dummy messages
    messages = []
    for i in range(10):
        m = MagicMock()
        m.id = i
        m.message = f"Message content {i}"
        m.out = False
        m.sender_id = 123
        m.date = "2023-01-01"
        messages.append(m)

    mock_client.get_messages.return_value = messages
    mock_client.get_entity.return_value = MagicMock()

    service = LearningService()
    service.client = mock_client

    # Mock internal methods
    with patch.object(service, "_save_message_to_db", return_value=1):
        with patch.object(service, "_analyze_and_extract", new_callable=AsyncMock) as mock_analyze:
            # Mock DB check for last synced ID to avoid SQL error
            service._get_last_synced_id = MagicMock(return_value=0)

            # Use MagicMock with a Future return value for asyncio.to_thread
            # to avoid AsyncMock warning complexities.
            with patch("asyncio.to_thread") as mock_to_thread:
                f = asyncio.Future()
                f.set_result(1)
                mock_to_thread.return_value = f

                # Handling side_effect if called multiple times or with different args?
                # The test calls it 10 times. A single future might be reused if not careful,
                # but awaiting a completed future multiple times is allowed.
                # Ideally, side_effect should return a NEW future each time.

                def to_thread_side_effect(func, *args, **kwargs):
                    f = asyncio.Future()
                    f.set_result(1)
                    return f

                mock_to_thread.side_effect = to_thread_side_effect

                # We also need to patch asyncio.sleep to avoid waiting
                with patch("asyncio.sleep", new_callable=AsyncMock):
                    result_msg = await service.ingest_history(chat_id=123, limit=10)

                    assert "Ingested 10 new messages" in result_msg.message
                    # Check if analyze was called for all 10 messages
                    assert mock_analyze.call_count == 10


# --- Reporting Service Tests ---


@pytest.mark.asyncio
async def test_reporting_service_grouping_logic():
    # Mock dependencies
    mock_client = AsyncMock()
    mock_ai_service = AsyncMock()

    service = ReportingService()

    # Mock database fetching
    msg1 = MagicMock()
    msg1.chat_id = 1
    msg1.text = "Msg 1"

    msg2 = MagicMock()
    msg2.chat_id = 1
    msg2.text = "Msg 2"

    msg3 = MagicMock()
    msg3.chat_id = 2
    msg3.text = "Msg 3"

    messages = [msg1, msg2, msg3]

    # Mock fetch_messages
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        # First call is fetch_messages, returns our list
        mock_thread.return_value = messages

        # Mock client.get_entity to return titles
        entity1 = MagicMock()
        entity1.title = "Group A"
        entity2 = MagicMock()
        entity2.title = "Group B"

        async def get_entity_side_effect(chat_id):
            if chat_id == 1:
                return entity1
            if chat_id == 2:
                return entity2
            return MagicMock(title="Unknown")

        # We need to patch the global 'client' used in reporting.py
        # But we can just set service.client since we init it
        service.client = mock_client
        mock_client.get_entity.side_effect = get_entity_side_effect

        # Patch ai_service imported in reporting.py
        with patch("backend.services.reporting.ai_service", mock_ai_service):
            mock_ai_service.summarize_conversations.return_value = "Summary"

            # Mock REPORT_CHANNEL_ID
            with patch("backend.services.reporting.settings") as mock_settings:
                mock_settings.REPORT_CHANNEL_ID = 999
                mock_settings.REPORT_CONTEXT_LIMIT = 2000
                mock_client.send_message.return_value = True

                await service.generate_daily_report()

                # Verify summarize_conversations was called with a dict
                args, _ = mock_ai_service.summarize_conversations.call_args
                data = args[0]

                assert isinstance(data, dict)
                # Keys now include ID
                assert "Group A (ID: 1)" in data
                assert "Group B (ID: 2)" in data
                assert len(data["Group A (ID: 1)"]) == 2
                assert len(data["Group B (ID: 2)"]) == 1


# --- AI Service Tests ---


@pytest.mark.asyncio
async def test_ai_service_summarize_grouped_data():
    service = AIService()
    mock_client = MagicMock()
    mock_response = MagicMock(text="Summary Result")
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    service.client = mock_client

    # Test with Dict
    data = {
        "Chat A": [
            MagicMock(sender_name="Alice", text="Hi", date=MagicMock(strftime=lambda x: "10:00"))
        ]
    }

    await service.summarize_conversations(data)

    # Check prompt content
    # generate_content(model=..., contents=...)
    kwargs = service.client.aio.models.generate_content.call_args.kwargs
    prompt = kwargs.get("contents")
    if not prompt:
        # Fallback to positional args
        args = service.client.aio.models.generate_content.call_args.args
        if len(args) > 1:
            prompt = args[1]

    assert "Chat A" in prompt
    assert "Alice" in prompt
    assert "Hi" in prompt
