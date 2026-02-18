import pytest
from unittest.mock import MagicMock, AsyncMock
from backend.services.command import CommandService


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
async def test_handle_start(service):
    """Test /start command."""
    result = await service.handle_command(123, "/start")

    assert result is True
    service.client.send_message.assert_called_once()
    args, _ = service.client.send_message.call_args
    assert args[0] == 123
    assert "Fala tu! Eu sou o Jules" in args[1]


@pytest.mark.asyncio
async def test_handle_ajuda(service):
    """Test /ajuda command."""
    result = await service.handle_command(123, "/ajuda")

    assert result is True
    service.client.send_message.assert_called_once()
    args, _ = service.client.send_message.call_args
    assert "Fala tu! Eu sou o Jules" in args[1]


@pytest.mark.asyncio
async def test_handle_help(service):
    """Test /help command."""
    result = await service.handle_command(123, "/help")

    assert result is True
    service.client.send_message.assert_called_once()
    args, _ = service.client.send_message.call_args
    assert "Fala tu! Eu sou o Jules" in args[1]
