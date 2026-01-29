import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from backend.services.ai import ai_service
from backend.services.reporting import reporting_service


@pytest.mark.asyncio
async def test_ai_service_extract_facts():
    # Mock the model
    mock_model = AsyncMock()
    mock_response = MagicMock()
    # Return a clean JSON list
    mock_response.text = (
        '[{"entity": "Test", "value": "Value", "category": "test"}]'
    )
    mock_model.generate_content_async.return_value = mock_response

    # Inject mock
    original_model = ai_service.model
    ai_service.model = mock_model

    try:
        facts = await ai_service.extract_facts("Some text")
        assert len(facts) == 1
        assert facts[0]["entity"] == "Test"
    finally:
        ai_service.model = original_model


@pytest.mark.asyncio
async def test_ai_service_extract_facts_with_markdown():
    # Mock the model with markdown code blocks
    mock_model = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = '```json\n[{"entity": "Test", "value": "Value"}]\n```'
    mock_model.generate_content_async.return_value = mock_response

    original_model = ai_service.model
    ai_service.model = mock_model

    try:
        facts = await ai_service.extract_facts("Some text")
        assert len(facts) == 1
        assert facts[0]["entity"] == "Test"
    finally:
        ai_service.model = original_model


@pytest.mark.asyncio
async def test_reporting_service_generate_daily_report():
    # Mock REPORT_CHANNEL_ID if needed, but we can patch it or rely on env
    with (
        patch("backend.services.reporting.REPORT_CHANNEL_ID", 123456),
        patch(
            "backend.services.reporting.client", new_callable=AsyncMock
        ) as mock_client,
        patch("backend.services.reporting.Session") as mock_session_cls,
        patch(
            "backend.services.ai.ai_service.summarize_conversations",
            new_callable=AsyncMock,
        ) as mock_summarize,
    ):

        # Mock fetch messages
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session

        # Create fake messages
        mock_msg = MagicMock()
        mock_msg.chat_id = 1
        mock_msg.date = datetime.now()
        mock_msg.sender_name = "Sender"
        mock_msg.text = "Hello"

        mock_session.exec.return_value.all.return_value = [mock_msg]

        # Mock AI summary
        mock_summarize.return_value = "Daily Summary Content"

        # Mock client.get_entity
        mock_entity = MagicMock()
        mock_entity.title = "Test Chat"
        mock_client.get_entity.return_value = mock_entity

        await reporting_service.generate_daily_report()

        # Verify client.send_message called
        assert mock_client.send_message.called
        args, _ = mock_client.send_message.call_args
        report_text = args[1]

        assert "# 📅 Relatório Diário de Conversas" in report_text
        assert "Daily Summary Content" in report_text
        assert "- **Total de Mensagens:** 1" in report_text
