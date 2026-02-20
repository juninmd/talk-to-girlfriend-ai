import pytest
from unittest.mock import AsyncMock, patch
from backend.services.learning import LearningService


@pytest.mark.asyncio
async def test_ingest_history_force_rescan():
    """Test that force_rescan=True uses min_id=0 (fetch latest messages)."""
    # Setup
    mock_client = AsyncMock()
    mock_client.get_entity = AsyncMock(return_value="mock_entity")
    # Return empty list to stop processing loop early
    mock_client.get_messages = AsyncMock(return_value=[])

    service = LearningService()
    service.client = mock_client

    # Patch the DB methods to avoid real DB calls
    with patch.object(service, "_get_last_synced_id", return_value=100) as mock_get_last_id:
        with patch.object(service, "_process_messages_ingestion", return_value=0):
            with patch.object(service, "_process_learning_batch", return_value=0):

                # Test with force_rescan=True
                await service.ingest_history(chat_id=123, limit=50, force_rescan=True)

                # Verify get_messages called with min_id=0
                mock_client.get_messages.assert_called_with("mock_entity", limit=50, min_id=0)

                # Verify _get_last_synced_id was NOT called
                mock_get_last_id.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_history_no_force_rescan():
    """Test that force_rescan=False uses last synced ID."""
    # Setup
    mock_client = AsyncMock()
    mock_client.get_entity = AsyncMock(return_value="mock_entity")
    mock_client.get_messages = AsyncMock(return_value=[])

    service = LearningService()
    service.client = mock_client

    # Patch the DB methods
    with patch.object(service, "_get_last_synced_id", return_value=999) as mock_get_last_id:
        with patch.object(service, "_process_messages_ingestion", return_value=0):
            with patch.object(service, "_process_learning_batch", return_value=0):

                # Test with force_rescan=False
                await service.ingest_history(chat_id=123, limit=50, force_rescan=False)

                # Verify get_messages called with min_id=999 (the mocked return value)
                mock_client.get_messages.assert_called_with("mock_entity", limit=50, min_id=999)
                mock_get_last_id.assert_called_once_with(123)
