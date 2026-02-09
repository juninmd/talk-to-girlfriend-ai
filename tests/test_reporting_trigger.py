import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.conversation import ConversationService


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_message = AsyncMock()
    return client


@pytest.fixture
def service(mock_client):
    service = ConversationService()
    service.client = mock_client
    return service


@pytest.mark.asyncio
async def test_handle_commands_relatorio_global(service):
    """Test that /relatorio_global triggers reporting service with chat_id=None."""
    with patch("backend.services.conversation.reporting_service") as mock_report:
        # Simulate successful report generation (returns text)
        mock_report.generate_daily_report = AsyncMock(return_value="# Daily Report")

        result = await service._handle_commands(123, "/relatorio_global")

        assert result is True
        # Verify it calls with chat_id=None (global mode)
        mock_report.generate_daily_report.assert_called_once_with(chat_id=None)

        # Verify messages sent: 1. "Generating...", 2. "Success!"
        assert service.client.send_message.call_count == 2

        # Check first message
        args1, _ = service.client.send_message.call_args_list[0]
        assert "Gerando e enviando relatório global" in args1[1]

        # Check success message
        args2, _ = service.client.send_message.call_args_list[1]
        assert "Relatório global enviado!" in args2[1]


@pytest.mark.asyncio
async def test_handle_commands_relatorio_global_failure(service):
    """Test that /relatorio_global handles empty report return (failure)."""
    with patch("backend.services.conversation.reporting_service") as mock_report:
        # Simulate failure (returns None or empty string)
        mock_report.generate_daily_report = AsyncMock(return_value=None)

        result = await service._handle_commands(123, "/relatorio_global")

        assert result is True
        mock_report.generate_daily_report.assert_called_once_with(chat_id=None)

        # Verify failure message
        args2, _ = service.client.send_message.call_args_list[1]
        assert "Falha ao gerar relatório" in args2[1]
