import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.ai import AIService

@pytest.fixture
def ai_service():
    with patch("backend.services.ai.genai.GenerativeModel") as mock_model_cls:
        mock_model = MagicMock()
        mock_model_cls.return_value = mock_model
        service = AIService()
        service.model = mock_model  # Ensure model is set
        return service

@pytest.mark.asyncio
async def test_extract_facts_json_success(ai_service):
    # Mock response
    mock_response = MagicMock()
    mock_response.text = '[{"entity": "Pizza", "value": "Likes pepperoni", "category": "preference"}]'
    ai_service.model.generate_content_async = AsyncMock(return_value=mock_response)

    facts = await ai_service.extract_facts("I love pepperoni pizza.")

    assert len(facts) == 1
    assert facts[0]["entity"] == "Pizza"
    assert facts[0]["value"] == "Likes pepperoni"

    # Verify we called with JSON mime type
    call_args = ai_service.model.generate_content_async.call_args
    assert call_args[1]["generation_config"]["response_mime_type"] == "application/json"

@pytest.mark.asyncio
async def test_extract_facts_json_cleanup(ai_service):
    # Mock response with markdown code blocks (even with JSON mode it can happen sometimes)
    mock_response = MagicMock()
    mock_response.text = '```json\n[{"entity": "Code", "value": "Python", "category": "tech"}]\n```'
    ai_service.model.generate_content_async = AsyncMock(return_value=mock_response)

    facts = await ai_service.extract_facts("I code in Python.")

    assert len(facts) == 1
    assert facts[0]["entity"] == "Code"

@pytest.mark.asyncio
async def test_extract_facts_empty(ai_service):
    mock_response = MagicMock()
    mock_response.text = "[]"
    ai_service.model.generate_content_async = AsyncMock(return_value=mock_response)

    facts = await ai_service.extract_facts("Nothing here.")
    assert facts == []

@pytest.mark.asyncio
async def test_summarize_conversations_success(ai_service):
    mock_response = MagicMock()
    mock_response.text = "**Resumo**\nDia tranquilo."
    ai_service.model.generate_content_async = AsyncMock(return_value=mock_response)

    from backend.database import Message
    from datetime import datetime

    msgs = [Message(
        telegram_message_id=1, chat_id=123, text="Hi",
        date=datetime.now(), is_outgoing=False
    )]

    summary = await ai_service.summarize_conversations(msgs)
    assert summary == "**Resumo**\nDia tranquilo."

@pytest.mark.asyncio
async def test_summarize_conversations_empty(ai_service):
    summary = await ai_service.summarize_conversations([])
    assert summary == "Sem dados para resumir."
