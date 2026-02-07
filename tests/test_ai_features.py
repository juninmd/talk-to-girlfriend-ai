import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os
import asyncio

# Set dummy env vars
os.environ["TELEGRAM_API_ID"] = "123"
os.environ["TELEGRAM_API_HASH"] = "abc"
os.environ["GOOGLE_API_KEY"] = "xyz"

from backend.services.ai import AIService  # noqa: E402
from backend.services.learning import LearningService  # noqa: E402


@pytest.mark.asyncio
async def test_fact_extraction():
    service = AIService()
    mock_client = MagicMock()
    mock_response = MagicMock(text='[{"entity": "Name", "value": "Alice", "category": "personal"}]')
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    service.client = mock_client

    facts = await service.extract_facts("My name is Alice")
    assert len(facts) == 1
    assert facts[0]["value"] == "Alice"


@pytest.mark.asyncio
async def test_ingest_history_flow():
    # We need to patch the client and database interactions
    with patch("backend.services.learning.client") as mock_client:
        mock_client.get_entity = AsyncMock(return_value="dummy_entity")

        # Create a mock message
        msg = MagicMock()
        msg.id = 100
        msg.message = "Hello world"
        msg.date = "2024-01-01"
        msg.out = False
        msg.sender_id = 999
        msg.sender.first_name = "Bob"
        msg.sender.last_name = None
        msg.sender.title = None

        # get_messages returns an iterable (or list)
        mock_client.get_messages = AsyncMock(return_value=[msg])

        service = LearningService()
        service.client = mock_client

        # Patch the helper methods we refactored
        service._fetch_history_messages = AsyncMock(return_value=[msg])
        service._process_learning_batch = AsyncMock()

        # Mock DB interaction for min_id
        # We need to patch Session to return a context manager that has a session with exec
        with patch("backend.services.learning.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value.__enter__.return_value = mock_session

            # exec().first() should return 0 or None. Let's return None (no history)
            mock_session.exec.return_value.first.return_value = None

            # Mock DB save (it's run in thread, so we patch asyncio.to_thread)
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                # First call is save_message, second is save_facts? No, ingest only calls save_message.
                # Actually process_messages_ingestion calls to_thread(save_message)
                mock_to_thread.return_value = 1  # DB ID

                result_msg = await service.ingest_history(123, limit=5)

                assert "Ingested 1 messages" in result_msg
                service._fetch_history_messages.assert_called_with("dummy_entity", 5, 0)
