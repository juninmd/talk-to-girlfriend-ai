import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.services.ai import AIService
from google.genai import types


@pytest.fixture
def ai_service():
    with patch("backend.services.ai.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        # We need to mock client.aio.models.generate_content
        # client.aio is a property usually, but we can just mock the chain
        mock_aio = MagicMock()
        mock_models = MagicMock()
        mock_generate_content = AsyncMock()

        mock_client.aio = mock_aio
        mock_aio.models = mock_models
        mock_models.generate_content = mock_generate_content

        service = AIService()
        # Explicitly set it again just in case init did something else (though init uses genai.Client())
        service.client = mock_client

        return service


@pytest.mark.asyncio
async def test_extract_facts_json_success(ai_service):
    # Mock response
    mock_response = MagicMock()
    mock_response.text = (
        '[{"entity": "Pizza", "value": "Likes pepperoni", "category": "preference"}]'
    )
    ai_service.client.aio.models.generate_content.return_value = mock_response

    facts = await ai_service.extract_facts("I love pepperoni pizza.")

    assert len(facts) == 1
    assert facts[0]["entity"] == "Pizza"
    assert facts[0]["value"] == "Likes pepperoni"

    # Verify we called with JSON mime type
    call_args = ai_service.client.aio.models.generate_content.call_args
    assert "config" in call_args.kwargs
    config = call_args.kwargs["config"]
    assert isinstance(config, types.GenerateContentConfig)
    assert config.response_mime_type == "application/json"


@pytest.mark.asyncio
async def test_extract_facts_json_cleanup(ai_service):
    # Mock response with markdown code blocks (even with JSON mode it can happen sometimes)
    mock_response = MagicMock()
    mock_response.text = (
        '```json\n[{"entity": "Code", "value": "Python", "category": "tech"}]\n```'
    )
    ai_service.client.aio.models.generate_content.return_value = mock_response

    facts = await ai_service.extract_facts("I code in Python.")

    assert len(facts) == 1
    assert facts[0]["entity"] == "Code"


@pytest.mark.asyncio
async def test_extract_facts_empty(ai_service):
    mock_response = MagicMock()
    mock_response.text = "[]"
    ai_service.client.aio.models.generate_content.return_value = mock_response

    facts = await ai_service.extract_facts("Nothing here.")
    assert facts == []


@pytest.mark.asyncio
async def test_summarize_conversations_success(ai_service):
    mock_response = MagicMock()
    mock_response.text = "**Resumo**\nDia tranquilo."
    ai_service.client.aio.models.generate_content.return_value = mock_response

    from backend.database import Message
    from datetime import datetime

    msgs = [
        Message(
            telegram_message_id=1, chat_id=123, text="Hi", date=datetime.now(), is_outgoing=False
        )
    ]

    summary = await ai_service.summarize_conversations(msgs)
    assert summary == "**Resumo**\nDia tranquilo."


@pytest.mark.asyncio
async def test_summarize_conversations_empty(ai_service):
    summary = await ai_service.summarize_conversations([])
    assert summary == "Sem dados para resumir."
