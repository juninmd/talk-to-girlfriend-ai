import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.learning import learning_service
from telethon import events
from telethon.tl.types import User

@pytest.mark.asyncio
async def test_learning_from_outgoing_message():
    """Verify that outgoing messages trigger fact extraction."""
    # Mock Event
    mock_event = MagicMock()
    mock_event.chat_id = 123
    mock_event.sender_id = 456
    mock_event.message.message = "Eu adoro programar em Python!"
    mock_event.message.id = 101
    mock_event.message.date = "2023-01-01"
    mock_event.message.out = True  # OUTGOING
    mock_event.sender = User(id=456, first_name="Me", last_name="Myself")

    # Mock DB save to return a valid ID
    with patch.object(learning_service, "_save_message_to_db", return_value=999) as mock_save:
        with patch("backend.services.learning.ai_service.extract_facts", new_callable=AsyncMock) as mock_extract:
            with patch.object(learning_service, "_save_facts_to_db") as mock_save_facts:
                mock_extract.return_value = [{"entity": "Python", "value": "Love it", "category": "tech"}]

                await learning_service.handle_message_learning(mock_event)

                # Allow async task to start
                await asyncio.sleep(0.01)

                # Verify save_message called
                mock_save.assert_called_once()
                # Verify extraction called (Crucial check for improvement)
                mock_extract.assert_called_once_with("Eu adoro programar em Python!")

@pytest.mark.asyncio
async def test_ignore_generated_reports():
    """Verify that generated reports are NOT learned."""
    # Mock Event
    mock_event = MagicMock()
    mock_event.chat_id = 123
    mock_event.sender_id = 456
    mock_event.message.message = "# 📅 Relatório Diário de Conversas\nbla bla"
    mock_event.message.id = 102
    mock_event.message.date = "2023-01-01"
    mock_event.message.out = True # Reports are usually outgoing
    mock_event.sender = User(id=456, first_name="Me", last_name="Myself")

    # Mock DB save
    with patch.object(learning_service, "_save_message_to_db", return_value=1000) as mock_save:
         with patch("backend.services.learning.ai_service.extract_facts", new_callable=AsyncMock) as mock_extract:

                await learning_service.handle_message_learning(mock_event)

                # Allow async task to start (if it were called)
                await asyncio.sleep(0.01)

                # Verify save_message called (we still save the log)
                mock_save.assert_called_once()
                # Verify extraction NOT called
                mock_extract.assert_not_called()
