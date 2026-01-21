import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import reactions

@pytest.fixture
def mock_client():
    with patch("backend.tools.reactions.client") as mock:
        yield mock

@pytest.mark.asyncio
async def test_send_reaction(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    result = await reactions.send_reaction(chat_id=123, message_id=1, emoji="❤️")
    assert "Reaction '❤️' sent" in result

@pytest.mark.asyncio
async def test_remove_reaction(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")
    mock_client.side_effect = AsyncMock()

    result = await reactions.remove_reaction(chat_id=123, message_id=1)
    assert "Reaction removed" in result

@pytest.mark.asyncio
async def test_get_message_reactions(mock_client):
    mock_client.get_input_entity = AsyncMock(return_value="peer")

    from telethon.tl.types import ReactionEmoji

    mock_result = MagicMock()
    mock_reaction = MagicMock()
    mock_reaction.peer_id.user_id = 999
    mock_reaction.reaction = ReactionEmoji(emoticon="🔥")
    mock_reaction.date = None
    mock_result.reactions = [mock_reaction]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await reactions.get_message_reactions(chat_id=123, message_id=1)
    # The emoji might be escaped in JSON, so check for unicode representation if needed
    # But usually simple chars are fine. "🔥" is \ud83d\udd25 in JSON sometimes.
    # We can check for user_id to be safe or decode result.
    import json
    data = json.loads(result)
    assert data["reactions"][0]["emoji"] == "🔥"
