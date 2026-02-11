import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.learning import learning_service
from telethon.tl.types import User
from backend.services.reporting import ReportingService


@pytest.mark.asyncio
async def test_learning_from_outgoing_message():
    """Verify that outgoing messages trigger fact extraction."""
    # Mock Event
    mock_event = MagicMock()
    mock_event.chat_id = 123
    mock_event.sender_id = 456
    mock_event.message.message = "Eu adoro programar em Python!"  # noqa: E501
    mock_event.message.id = 101
    mock_event.message.date = "2023-01-01"
    mock_event.message.out = True  # OUTGOING  # noqa: E501
    mock_event.sender = User(id=456, first_name="Me", last_name="Myself")

    # Mock DB save to return a valid ID
    with patch.object(learning_service, "_save_message_to_db", return_value=999) as mock_save:
        with patch(
            "backend.services.learning.ai_service.extract_facts", new_callable=AsyncMock
        ) as mock_extract:
            with patch.object(learning_service, "_save_facts_to_db"):
                mock_extract.return_value = [
                    {"entity": "Python", "value": "Love it", "category": "tech"}
                ]

                # Capture the background task
                with patch("backend.services.learning.asyncio.create_task") as mock_create_task:
                    # Mock create_task to behave like a pass-through or return a dummy task,
                    # but we want to await the coroutine it received.

                    # Setup side_effect to capture the coro
                    captured_coros = []

                    def side_effect(coro):
                        captured_coros.append(coro)
                        return MagicMock()  # Return a dummy task

                    mock_create_task.side_effect = side_effect

                    await learning_service.handle_message_learning(mock_event)

                    # Verify create_task was called
                    assert mock_create_task.called

                    # Manually await the captured coroutine to prevent "never awaited" warning
                    # and to execute the extraction logic
                    if captured_coros:
                        await captured_coros[0]

                # Verify save_message called
                mock_save.assert_called_once()
                # Verify extraction called (Crucial check for improvement)
                mock_extract.assert_called_once_with("Eu adoro programar em Python!")  # noqa: E501


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
    mock_event.message.out = True  # Reports are usually outgoing
    mock_event.sender = User(id=456, first_name="Me", last_name="Myself")

    # Mock DB save
    with patch.object(learning_service, "_save_message_to_db", return_value=1000) as mock_save:
        with patch(
            "backend.services.learning.ai_service.extract_facts", new_callable=AsyncMock
        ) as mock_extract:

            with patch("backend.services.learning.asyncio.create_task") as mock_create_task:
                await learning_service.handle_message_learning(mock_event)

                # Should NOT spawn a task for reports
                mock_create_task.assert_not_called()

            # Verify save_message called (we still save the log)
            mock_save.assert_called_once()
            # Verify extraction NOT called
            mock_extract.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_target_entity_with_string_id():
    # Setup
    service = ReportingService()
    service.client = AsyncMock()

    # Mock settings
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = "-1001234567890"

        # Mock client.get_entity to return a dummy entity when called with int
        expected_id = -1001234567890
        mock_entity = AsyncMock()
        mock_entity.id = expected_id
        service.client.get_entity.return_value = mock_entity

        # Execute
        result = await service._resolve_target_entity()

        # Verify
        # The key verification: verify get_entity was called with an INTEGER, not a string
        service.client.get_entity.assert_called_with(expected_id)
        assert result.id == expected_id


@pytest.mark.asyncio
async def test_resolve_target_entity_with_int_id():
    # Setup
    service = ReportingService()
    service.client = AsyncMock()

    # Mock settings
    with patch("backend.services.reporting.settings") as mock_settings:
        expected_id = -1009876543210
        mock_settings.REPORT_CHANNEL_ID = expected_id

        mock_entity = AsyncMock()
        mock_entity.id = expected_id
        service.client.get_entity.return_value = mock_entity

        # Execute
        result = await service._resolve_target_entity()

        # Verify
        service.client.get_entity.assert_called_with(expected_id)
        assert result.id == expected_id


def test_ai_context_fact_limit():
    from backend.settings import settings
    # We modified this to 5000
    assert settings.AI_CONTEXT_FACT_LIMIT == 5000
