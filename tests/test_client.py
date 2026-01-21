import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.client import get_client, MockClient

@patch("backend.client.TELEGRAM_API_ID", None)
def test_get_client_mock():
    # Force mock client
    c = get_client()
    assert isinstance(c, MockClient)

@patch("backend.client.TELEGRAM_API_ID", "123")
@patch("backend.client.TELEGRAM_API_HASH", "abc")
@patch("backend.client.SESSION_STRING", "session")
def test_get_client_string_session():
    # We must patch StringSession because the real one validates the string
    with patch("backend.client.StringSession") as mock_ss:
        with patch("backend.client.TelegramClient") as mock_tc:
            c = get_client()
            mock_tc.assert_called_once()
            # Check if StringSession was used
            mock_ss.assert_called_with("session")
            args, _ = mock_tc.call_args
            assert args[0] == mock_ss.return_value

@patch("backend.client.TELEGRAM_API_ID", "123")
@patch("backend.client.TELEGRAM_API_HASH", "abc")
@patch("backend.client.SESSION_STRING", None)
@patch("backend.client.TELEGRAM_SESSION_NAME", "session_file")
def test_get_client_file_session():
    with patch("backend.client.TelegramClient") as mock_tc:
        c = get_client()
        mock_tc.assert_called_once()
        args, _ = mock_tc.call_args
        assert args[0] == "session_file"

@pytest.mark.asyncio
async def test_mock_client_methods():
    c = MockClient()
    await c.start()
    c.add_event_handler(None)

    async with c.action():
        pass

    await c.send_message("test")
    res = await c.get_entity("test")
    assert res is None
    await c.run_until_disconnected()
