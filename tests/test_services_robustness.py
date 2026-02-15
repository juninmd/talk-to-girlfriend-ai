import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.learning import LearningService
from backend.services.reporting import ReportingService
from backend.services.ai import AIService
from telethon.tl.types import User

@pytest.mark.asyncio
async def test_learning_from_outgoing_message_robust():
    """Verify that outgoing messages trigger fact extraction correctly."""
    service = LearningService()

    # Mock dependencies
    service.client = MagicMock()
    service._me = None # Reset me

    mock_event = MagicMock()
    mock_event.chat_id = 123
    mock_event.sender_id = 456
    mock_event.message.message = "Eu adoro programar em Python!"
    mock_event.message.id = 101
    mock_event.message.date = "2023-01-01"
    mock_event.message.out = True  # OUTGOING
    mock_event.sender = User(id=456, first_name="Me", last_name="Myself")

    with patch.object(service, "_save_message_to_db", return_value=999) as mock_save:
        with patch.object(service, "_analyze_and_extract", new_callable=AsyncMock) as mock_extract:
             # Mock _get_me to return a user (not bot)
            with patch.object(service, "_get_me", new_callable=AsyncMock) as mock_get_me:
                mock_user = MagicMock()
                mock_user.bot = False
                mock_get_me.return_value = mock_user

                # We need to ensure asyncio.create_task is called and we await the coro
                with patch("asyncio.create_task") as mock_create_task:
                    # Capture the coroutine
                    captured_coros = []
                    def side_effect(coro):
                        captured_coros.append(coro)
                        return MagicMock()
                    mock_create_task.side_effect = side_effect

                    await service.handle_message_learning(mock_event)

                    assert mock_create_task.called
                    if captured_coros:
                        await captured_coros[0]

                    mock_extract.assert_called_once()


@pytest.mark.asyncio
async def test_reporting_resolve_target_entity_variations():
    service = ReportingService()
    service.client = AsyncMock()

    # Case 1: Int ID
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = -100123
        service.client.get_entity.return_value = MagicMock(id=-100123)

        entity = await service._resolve_target_entity()
        service.client.get_entity.assert_called_with(-100123)
        assert entity.id == -100123

    # Case 2: String Int ID
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = "-100456"
        service.client.get_entity.return_value = MagicMock(id=-100456)

        entity = await service._resolve_target_entity()
        service.client.get_entity.assert_called_with(-100456)
        assert entity.id == -100456

    # Case 3: Username (String)
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = "@mychannel"
        service.client.get_entity.return_value = MagicMock(id=789)

        entity = await service._resolve_target_entity()
        service.client.get_entity.assert_called_with("@mychannel")
        assert entity.id == 789

    # Case 4: None (Fallback)
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = None
        service.client.get_me.return_value = MagicMock(id=111)

        entity = await service._resolve_target_entity()
        service.client.get_me.assert_called()
        assert entity.id == 111


@pytest.mark.asyncio
async def test_ai_json_cleaning_robustness():
    service = AIService()

    # Case: Single Object (not list) - Should be handled or validated
    # Current implementation expects list structure `[...]`.
    # If the LLM returns a single object `{}`, _clean_json_response will return `{}`.
    # json.loads will parse it as dict.
    # _validate_facts expects list.

    # Let's verify _clean_json_response behavior

    # Case: Markdown JSON (uppercase)
    text = "```JSON\n[{\"a\": 1}]\n```"
    cleaned = service._clean_json_response(text)
    assert cleaned == "[{\"a\": 1}]"

    # Case: Markdown without type
    text = "```\n[{\"a\": 1}]\n```"
    cleaned = service._clean_json_response(text)
    assert cleaned == "[{\"a\": 1}]"

    # Case: Trailing comma in list
    text = "[{\"a\": 1},]"
    cleaned = service._clean_json_response(text)
    assert cleaned == "[{\"a\": 1}]"
