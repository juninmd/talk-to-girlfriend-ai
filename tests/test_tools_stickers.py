import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import stickers


@pytest.fixture
def mock_client():
    with patch("backend.tools.stickers.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_sticker_sets(mock_client):
    mock_result = MagicMock()
    mock_set = MagicMock()
    mock_set.title = "Pack1"
    mock_result.sets = [mock_set]
    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await stickers.get_sticker_sets()
    assert "Pack1" in result


@pytest.mark.asyncio
async def test_send_sticker(mock_client):
    with patch("os.path.isfile", return_value=True):
        mock_client.get_entity = AsyncMock(return_value="peer")
        mock_client.send_file = AsyncMock()

        result = await stickers.send_sticker(
            chat_id=123, file_path="sticker.webp"
        )
        assert "Sticker sent" in result


@pytest.mark.asyncio
async def test_get_gif_search(mock_client):
    mock_result = MagicMock()
    mock_gif = MagicMock()
    # document.id must be int to be json serializable
    mock_gif.document.id = 999
    # Set both gifs (for primary path) and messages (for fallback path)
    mock_result.gifs = [mock_gif]

    # Mock message for fallback path
    mock_msg = MagicMock()
    mock_msg.media.document.id = 999
    mock_result.messages = [mock_msg]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await stickers.get_gif_search("fun")
    assert "999" in result


@pytest.mark.asyncio
async def test_send_gif(mock_client):
    mock_client.get_entity = AsyncMock(return_value="peer")
    mock_client.send_file = AsyncMock()

    result = await stickers.send_gif(chat_id=123, gif_id=999)
    assert "GIF sent" in result
