import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.services.learning import LearningService, LearningResult

@pytest.mark.asyncio
async def test_ingest_all_history():
    """Test global ingestion of multiple chats."""

    # 1. Setup Mock Dialogs
    mock_chat1 = MagicMock()
    mock_chat1.id = 101
    mock_chat1.is_channel = False

    mock_chat2 = MagicMock()
    mock_chat2.id = 102
    mock_chat2.is_channel = False

    mock_channel = MagicMock()
    mock_channel.id = 201
    mock_channel.is_channel = True

    mock_dialogs = [mock_chat1, mock_channel, mock_chat2]

    # 2. Setup Service and Mocks
    service = LearningService()
    service.client = AsyncMock()
    service.client.get_dialogs = AsyncMock(return_value=mock_dialogs)

    # Mock ingest_history to simulate learning
    # First call returns 2 facts, second returns 3 facts
    with patch.object(service, "ingest_history") as mock_ingest:
        mock_ingest.side_effect = [
            LearningResult(messages_count=10, facts_count=2, message="Ingested 10 messages. Learned 2 new facts."),
            LearningResult(messages_count=5, facts_count=3, message="Ingested 5 messages. Learned 3 new facts.")
        ]

        # 3. Run Method
        result = await service.ingest_all_history(limit_dialogs=5, msgs_limit=20)

        # 4. Assertions

        # Should call get_dialogs with limit=5
        service.client.get_dialogs.assert_called_once_with(limit=5)

        # Should call ingest_history twice (for chat1 and chat2, skipping channel)
        assert mock_ingest.call_count == 2
        mock_ingest.assert_any_call(101, limit=20, force_rescan=False)
        mock_ingest.assert_any_call(102, limit=20, force_rescan=False)

        # Should NOT call for channel
        # Use a check to ensure 201 wasn't passed
        calls = [args[0] for args, _ in mock_ingest.call_args_list]
        assert 201 not in calls

        # Check result string parsing
        # Total facts = 2 + 3 = 5
        # Total chats = 2
        assert "Processed 2 chats" in result
        assert "Total new facts learned: 5" in result
