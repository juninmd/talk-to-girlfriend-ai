import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.command import CommandService
from backend.database import Fact


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.send_message = AsyncMock()
    return client


@pytest.fixture
def service(mock_client):
    service = CommandService(mock_client)
    return service


@pytest.mark.asyncio
async def test_handle_commands_aprender(service):
    with patch("backend.services.command.learning_service") as mock_learn:
        result_obj = MagicMock()
        result_obj.message = "Ingested 10 messages"
        mock_learn.ingest_history = AsyncMock(return_value=result_obj)

        result = await service.handle_command(123, "/aprender 20")

        assert result is True
        mock_learn.ingest_history.assert_called_once_with(123, 20, force_rescan=True)
        assert service.client.send_message.call_count == 2  # Starting + Done


@pytest.mark.asyncio
async def test_handle_commands_relatorio(service):
    with patch("backend.services.command.reporting_service") as mock_report:
        mock_report.generate_daily_report = AsyncMock(return_value="Report Content")

        result = await service.handle_command(123, "/relatorio")

        assert result is True
        mock_report.generate_daily_report.assert_called_once_with(chat_id=123)
        assert service.client.send_message.call_count == 2


@pytest.mark.asyncio
async def test_handle_commands_fatos_empty(service):
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = []

        result = await service.handle_command(123, "/fatos")

        assert result is True
        service.client.send_message.assert_any_call(123, "🧠 Buscando fatos conhecidos...")
        service.client.send_message.assert_any_call(
            123, "🤷‍♂️ Não conheço nenhum fato sobre esta conversa (ou você) ainda."
        )


@pytest.mark.asyncio
async def test_handle_commands_fatos_found(service):
    facts = [
        Fact(entity_name="Alice", value="Software Engineer", category="work"),
        Fact(entity_name="Bob", value="Pizza", category="preference"),
    ]

    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = facts

        result = await service.handle_command(123, "/fatos")

        assert result is True
        # Check if the message contains the facts
        args, _ = service.client.send_message.call_args_list[-1]
        msg_text = args[1]
        assert "Alice: Software Engineer" in msg_text
        assert "Bob: Pizza" in msg_text
        assert "_Work_" in msg_text
        assert "_Preference_" in msg_text


@pytest.mark.asyncio
async def test_handle_commands_unknown(service):
    result = await service.handle_command(123, "Hello world")
    assert result is False
    service.client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_commands_start(service):
    result = await service.handle_command(123, "/start")
    assert result is True
    # Verify new content
    args, _ = service.client.send_message.call_args
    assert "Fala tu! Eu sou o Jules" in args[1]
