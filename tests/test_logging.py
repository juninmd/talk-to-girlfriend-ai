from unittest.mock import patch
from backend.logging_setup import setup_logging


def test_setup_logging():
    with patch("logging.basicConfig") as mock_basic_config:
        with patch("logging.getLogger") as mock_get_logger:
            setup_logging()
            mock_basic_config.assert_called_once()
            assert mock_get_logger.call_count >= 3
