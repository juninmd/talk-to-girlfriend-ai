import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.services.reporting import ReportingService


@pytest.fixture
def mock_session():
    with patch("backend.services.reporting.Session") as mock:
        yield mock


@pytest.fixture
def mock_client():
    with patch("backend.services.reporting.client") as mock:
        yield mock


@pytest.fixture
def mock_ai_service():
    with patch("backend.services.reporting.ai_service") as mock:
        yield mock


@pytest.mark.asyncio
async def test_generate_daily_report_no_messages(mock_session, mock_client):
    # Mock empty messages
    with patch("backend.services.reporting.settings") as mock_settings:
        mock_settings.REPORT_CHANNEL_ID = 123
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = []

            service = ReportingService()
            await service.generate_daily_report()

            mock_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_generate_daily_report_with_messages(mock_session, mock_client, mock_ai_service):
    # Mock messages
    mock_msg = MagicMock()
    mock_msg.chat_id = 123

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = [mock_msg]

        mock_ai_service.summarize_conversations = AsyncMock(return_value="Summary")

        with patch("backend.services.reporting.settings") as mock_settings:
            mock_settings.REPORT_CHANNEL_ID = -100
            mock_settings.REPORT_CONTEXT_LIMIT = 1000

            mock_entity = MagicMock()
            mock_entity.id = 100
            mock_client.get_entity = AsyncMock(return_value=mock_entity)
            mock_client.send_message = AsyncMock()

            service = ReportingService()
            await service.generate_daily_report()

            mock_client.send_message.assert_called()
            args, _ = mock_client.send_message.call_args
            assert "Summary" in args[1]
            assert "Estatísticas" in args[1]


@pytest.mark.asyncio
async def test_generate_daily_report_no_channel_id(mock_session, mock_client, mock_ai_service):
    # Test Fallback to Saved Messages
    mock_msg = MagicMock()
    mock_client.get_me = AsyncMock(return_value=MagicMock(id=12345))
    mock_client.send_message = AsyncMock()

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = [mock_msg]
        mock_ai_service.summarize_conversations = AsyncMock(return_value="Summary")

        with patch("backend.services.reporting.settings") as mock_settings:
            mock_settings.REPORT_CHANNEL_ID = None
            mock_settings.REPORT_CONTEXT_LIMIT = 1000
            service = ReportingService()
            await service.generate_daily_report()

            # Should call get_me and then send_message
            mock_client.get_me.assert_called_once()
            mock_client.send_message.assert_called_once()
