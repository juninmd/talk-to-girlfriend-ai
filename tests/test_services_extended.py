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
    service._save_message_to_db = MagicMock(return_value=1)  # Returns DB ID
    service._analyze_and_extract = AsyncMock()

    # We need to mock asyncio.to_thread to just call the function synchronously or return a value
    # In the code: await asyncio.to_thread(self._save_message_to_db, msg_data)
    # So we can just make it run the function.

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_to_thread.side_effect = lambda func, *args: func(*args)

        # We also need to patch asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", new_callable=AsyncMock):
            count = await service.ingest_history(chat_id=123, limit=10)

            assert count == 10
            # Check if analyze was called for all 10 messages (since they are all valid text > 5 chars)
            assert service._analyze_and_extract.call_count == 10


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

        # We need to patch the global 'client' used in reporting.py, not an instance attr
        with patch("backend.services.reporting.client", mock_client):
            service.client = mock_client
            mock_client.get_entity.side_effect = get_entity_side_effect

            with patch("backend.services.reporting.ai_service", mock_ai_service):
                mock_ai_service.summarize_conversations.return_value = "Summary"

                # Mock REPORT_CHANNEL_ID
                with patch("backend.services.reporting.settings") as mock_settings:
                    mock_settings.REPORT_CHANNEL_ID = 999
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
    service.model = AsyncMock()
    service.model.generate_content_async.return_value.text = "Summary Result"

    # Test with Dict
    data = {
        "Chat A": [
            MagicMock(sender_name="Alice", text="Hi", date=MagicMock(strftime=lambda x: "10:00"))
        ]
    }

    await service.summarize_conversations(data)

    # Check prompt content
    args, _ = service.model.generate_content_async.call_args
    prompt = args[0]
    assert "Chat A" in prompt
    assert "Alice" in prompt
    assert "Hi" in prompt
