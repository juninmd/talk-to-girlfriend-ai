from unittest.mock import MagicMock, patch
from backend.database import get_session, create_db_and_tables


def test_get_session():
    with patch("backend.database.Session") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session

        gen = get_session()
        session = next(gen)
        assert session == mock_session


def test_create_db_and_tables():
    with patch("backend.database.SQLModel.metadata.create_all") as mock_create:
        create_db_and_tables()
        mock_create.assert_called_once()
