import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import bots


@pytest.fixture
def mock_client():
    with patch("backend.tools.bots.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_bot_info(mock_client):
    mock_entity = MagicMock()
    mock_entity.id = 123
    mock_entity.first_name = "TestBot"
    mock_client.get_entity = AsyncMock(return_value=mock_entity)

    mock_full = MagicMock()
    mock_full.to_dict.return_value = {"id": 123, "about": "A bot"}

    mock_client.side_effect = AsyncMock(return_value=mock_full)

    result = await bots.get_bot_info("TestBot")
    assert "A bot" in result


@pytest.mark.asyncio
async def test_set_bot_commands(mock_client):
    mock_me = MagicMock()
    mock_me.bot = True
    mock_client.get_me = AsyncMock(return_value=mock_me)
    mock_client.side_effect = AsyncMock()  # client() call

    result = await bots.set_bot_commands(
        "MyBot", [{"command": "start", "description": "Start"}]
    )
    assert "Bot commands set" in result


@pytest.mark.asyncio
async def test_set_bot_commands_not_bot(mock_client):
    mock_me = MagicMock()
    mock_me.bot = False
    mock_client.get_me = AsyncMock(return_value=mock_me)

    result = await bots.set_bot_commands("MyBot", [])
    assert "for bot accounts only" in result
