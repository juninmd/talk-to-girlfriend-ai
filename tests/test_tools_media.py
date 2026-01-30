import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import media


@pytest.fixture
def mock_client():
    with patch("backend.tools.media.client") as mock:
        yield mock


@pytest.fixture
def mock_os():
    with patch("backend.tools.media.os") as mock:
        yield mock


@pytest.mark.asyncio
async def test_send_file(mock_client, mock_os):
    mock_os.path.isfile.return_value = True
    mock_os.access.return_value = True

    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.send_file = AsyncMock()

    result = await media.send_file(chat_id=123, file_path="test.jpg")
    assert "File sent" in result
    mock_client.send_file.assert_called_with(mock_entity, "test.jpg", caption=None)


@pytest.mark.asyncio
async def test_send_file_not_found(mock_client, mock_os):
    mock_os.path.isfile.return_value = False
    result = await media.send_file(chat_id=123, file_path="test.jpg")
    assert "File not found" in result


@pytest.mark.asyncio
async def test_download_media(mock_client, mock_os):
    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)

    mock_msg = MagicMock()
    mock_msg.media = True
    mock_client.get_messages = AsyncMock(return_value=mock_msg)

    mock_os.access.return_value = True
    mock_os.path.dirname.return_value = "."
    mock_os.path.isfile.return_value = True

    mock_client.download_media = AsyncMock()

    result = await media.download_media(chat_id=123, message_id=1, file_path="out.jpg")
    assert "Media downloaded" in result


@pytest.mark.asyncio
async def test_send_voice(mock_client, mock_os):
    mock_os.path.isfile.return_value = True

    mock_entity = MagicMock()
    mock_client.get_entity = AsyncMock(return_value=mock_entity)
    mock_client.send_file = AsyncMock()

    result = await media.send_voice(chat_id=123, file_path="voice.ogg")
    assert "Voice message sent" in result


@pytest.mark.asyncio
async def test_send_voice_invalid(mock_client, mock_os):
    mock_os.path.isfile.return_value = True
    result = await media.send_voice(chat_id=123, file_path="text.txt")
    assert "must be .ogg or .opus" in result
