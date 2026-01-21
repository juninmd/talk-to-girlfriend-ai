import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from backend.tools import contacts

@pytest.fixture
def mock_client():
    with patch("backend.tools.contacts.client") as mock:
        yield mock

@pytest.mark.asyncio
async def test_list_contacts(mock_client):
    # Mock result of client(GetContactsRequest)
    mock_result = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 123
    mock_user.first_name = "Alice"
    mock_user.last_name = "Doe"
    mock_user.username = "alice"
    mock_user.phone = "1234"
    mock_result.users = [mock_user]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await contacts.list_contacts()
    assert "Alice Doe" in result
    assert "123" in result

@pytest.mark.asyncio
async def test_search_contacts(mock_client):
    mock_result = MagicMock()
    mock_user = MagicMock()
    mock_user.id = 456
    mock_user.first_name = "Bob"
    mock_result.users = [mock_user]

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await contacts.search_contacts("Bob")
    assert "Bob" in result
    assert "456" in result

@pytest.mark.asyncio
async def test_add_contact(mock_client):
    mock_result = MagicMock()
    mock_result.imported = True

    mock_client.side_effect = AsyncMock(return_value=mock_result)

    result = await contacts.add_contact("12345", "Charlie")
    assert "added successfully" in result

@pytest.mark.asyncio
async def test_delete_contact(mock_client):
    mock_client.get_entity = AsyncMock(return_value="user_obj")
    mock_client.side_effect = AsyncMock() # For the delete request

    result = await contacts.delete_contact(user_id=123)
    assert "deleted" in result
    mock_client.get_entity.assert_called_with(123)
