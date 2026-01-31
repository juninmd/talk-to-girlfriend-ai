import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import misc


@pytest.fixture
def mock_client():
    with patch("backend.tools.misc.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_me(mock_client):
    from telethon.tl.types import User

    # Use spec to ensure proper isinstance checks if format_entity uses it
    mock_user = MagicMock(spec=User)
    mock_user.id = 123
    mock_user.username = "test"
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.phone = "123456"

    mock_client.get_me = AsyncMock(return_value=mock_user)

    result = await misc.get_me()
    import json

    data = json.loads(result)
    assert data["id"] == 123
    assert data["username"] == "test"


@pytest.mark.asyncio
async def test_get_me_error(mock_client):
    mock_client.get_me = AsyncMock(side_effect=Exception("Error"))
    result = await misc.get_me()
    # log_and_format_error masks the message code unless user_message is set
    assert "An error occurred" in result


@pytest.mark.asyncio
async def test_get_participants(mock_client):
    from telethon.tl.types import User

    mock_user = MagicMock(spec=User)
    mock_user.id = 123
    mock_user.first_name = "Test"
    mock_user.last_name = None
    mock_user.username = None
    mock_user.phone = None

    # get_participants returns an async iterator or list
    mock_client.get_participants = AsyncMock(return_value=[mock_user])

    result = await misc.get_participants(chat_id=100)
    # get_participants returns a string, not JSON
    assert "ID: 123" in result
    assert "Name: Test" in result


@pytest.mark.asyncio
async def test_get_participants_error(mock_client):
    mock_client.get_participants = AsyncMock(side_effect=Exception("Error"))
    result = await misc.get_participants(chat_id=100)
    assert "An error occurred" in result
