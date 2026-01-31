import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import chat


@pytest.fixture
def mock_client():
    with patch("backend.tools.chat.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_list_chats_extended(mock_client):
    from telethon.tl.types import User, Chat, Channel

    # Dialog 1: User
    d1 = MagicMock()
    d1.entity = MagicMock(spec=User)
    d1.entity.id = 1
    d1.entity.first_name = "User1"
    d1.entity.last_name = "Doe"
    d1.entity.username = "user1"
    d1.unread_count = 5

    # Dialog 2: Chat
    d2 = MagicMock()
    d2.entity = MagicMock(spec=Chat)
    d2.entity.id = 2
    d2.entity.title = "Group1"
    d2.unread_count = 0
    d2.dialog.unread_mark = True

    # Dialog 3: Channel (Broadcast)
    d3 = MagicMock()
    d3.entity = MagicMock(spec=Channel)
    d3.entity.id = 3
    d3.entity.title = "Channel1"
    d3.entity.broadcast = True
    d3.entity.username = "chan1"
    d3.unread_count = 0
    d3.dialog.unread_mark = False

    # Dialog 4: Supergroup (Channel non-broadcast)
    d4 = MagicMock()
    d4.entity = MagicMock(spec=Channel)
    d4.entity.id = 4
    d4.entity.title = "Supergroup1"
    d4.entity.broadcast = False
    d4.unread_count = 0
    d4.dialog.unread_mark = False

    mock_client.get_dialogs = AsyncMock(return_value=[d1, d2, d3, d4])

    # Test all
    res = await chat.list_chats(limit=10)
    assert "User1 Doe" in res
    assert "Group1" in res
    assert "Channel1" in res
    assert "Supergroup1" in res
    assert "Unread: 5" in res
    assert "Unread: marked" in res

    # Test filter user
    res = await chat.list_chats(chat_type="user")
    assert "User1" in res
    assert "Group1" not in res

    # Test filter group (matches Chat and Supergroup)
    res = await chat.list_chats(chat_type="group")
    assert "Group1" in res
    assert "Supergroup1" in res
    assert "User1" not in res

    # Test filter channel
    res = await chat.list_chats(chat_type="channel")
    assert "Channel1" in res
    assert "Group1" not in res


@pytest.mark.asyncio
async def test_get_chat_extended(mock_client):
    from telethon.tl.types import User, Chat, Channel

    # Case: Channel/Megagroup
    c = MagicMock(spec=Channel)
    c.id = 100
    c.title = "Mega"
    c.broadcast = False
    c.megagroup = True
    c.username = "mega"

    mock_client.get_entity = AsyncMock(return_value=c)
    # mock participants count
    mock_client.get_participants = AsyncMock(return_value=MagicMock(total=50))

    res = await chat.get_chat(chat_id=100)
    assert "Supergroup" in res
    assert "Participants: 50" in res

    # Case: Basic Chat
    bc = MagicMock(spec=Chat)
    bc.id = 200
    bc.title = "Basic"
    mock_client.get_entity = AsyncMock(return_value=bc)
    res = await chat.get_chat(chat_id=200)
    assert "Group (Basic)" in res

    # Case: User
    u = MagicMock(spec=User)
    u.id = 300
    u.first_name = "Alice"
    u.last_name = None
    u.username = None
    u.phone = None
    u.bot = True
    u.verified = True
    mock_client.get_entity = AsyncMock(return_value=u)
    res = await chat.get_chat(chat_id=300)
    assert "Bot: Yes" in res
    assert "Verified: Yes" in res


@pytest.mark.asyncio
async def test_leave_chat_extended(mock_client):
    from telethon.tl.types import User, Chat

    # Leave basic chat
    c = MagicMock(spec=Chat)
    c.id = 1
    c.title = "Basic"
    mock_client.get_entity = AsyncMock(return_value=c)
    mock_client.get_me = AsyncMock(return_value=MagicMock(id=99))
    mock_client.side_effect = AsyncMock()  # client() calls

    res = await chat.leave_chat(chat_id=1)
    assert "Left basic group" in res

    # Leave invalid type
    u = MagicMock(spec=User)
    u.id = 2
    mock_client.get_entity = AsyncMock(return_value=u)

    res = await chat.leave_chat(chat_id=2)
    assert "An error occurred" in res


@pytest.mark.asyncio
async def test_chat_exceptions(mock_client):
    mock_client.get_dialogs = AsyncMock(side_effect=Exception("Dialogs Error"))
    res = await chat.get_chats()
    assert "An error occurred" in res

    mock_client.get_entity = AsyncMock(side_effect=Exception("Entity Error"))
    res = await chat.get_chat(1)
    assert "An error occurred" in res
