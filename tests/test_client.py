import pytest
from unittest.mock import patch

from backend.client import get_client, MockClient


def test_get_client_mock():
    # Force mock client
    with patch("backend.client.settings") as mock_settings:
        # Mock attributes to be Falsy
        mock_settings.TELEGRAM_API_ID = 0
        mock_settings.TELEGRAM_API_HASH = ""

        c = get_client()
        assert isinstance(c, MockClient)


def test_get_client_string_session():
    # We must patch StringSession because the real one validates the string
    with patch("backend.client.settings") as mock_settings:
        mock_settings.TELEGRAM_API_ID = 123
        mock_settings.TELEGRAM_API_HASH = "abc"
        mock_settings.TELEGRAM_SESSION_STRING = "session"

        with patch("backend.client.StringSession") as mock_ss:
            with patch("backend.client.TelegramClient") as mock_tc:
                get_client()
                mock_tc.assert_called_once()
                # Check if StringSession was used
                mock_ss.assert_called_with("session")
                args, _ = mock_tc.call_args
                assert args[0] == mock_ss.return_value


def test_get_client_file_session():
    with patch("backend.client.settings") as mock_settings:
        mock_settings.TELEGRAM_API_ID = 123
        mock_settings.TELEGRAM_API_HASH = "abc"
        mock_settings.TELEGRAM_SESSION_STRING = None
        mock_settings.TELEGRAM_SESSION_NAME = "session_file"

        with patch("backend.client.TelegramClient") as mock_tc:
            get_client()
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
