import pytest
from unittest.mock import AsyncMock, patch

from backend.tools import learning


@pytest.fixture
def mock_learning_service():
    with patch("backend.tools.learning.learning_service") as mock:
        yield mock


@pytest.mark.asyncio
async def test_learn_from_chat(mock_learning_service):
    mock_learning_service.ingest_history = AsyncMock(return_value=50)

    result = await learning.learn_from_chat(chat_id=123, limit=50)
    assert "ingested 50 messages" in result
    mock_learning_service.ingest_history.assert_called_with(123, 50)
