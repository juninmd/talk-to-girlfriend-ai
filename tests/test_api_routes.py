import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.api.routes import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


@pytest.fixture
def mock_telegram_service():
    with patch("backend.api.routes.TelegramService") as mock:
        yield mock


def test_health_check():
    with patch("backend.client.client") as mock_client:
        mock_client.is_connected.return_value = True
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["connected"] is True


def test_get_me(mock_telegram_service):
    mock_telegram_service.get_me = AsyncMock(return_value={"id": 123})
    response = client.get("/me")
    assert response.status_code == 200
    assert response.json()["id"] == 123


def test_get_me_error(mock_telegram_service):
    mock_telegram_service.get_me = AsyncMock(side_effect=Exception("Error"))
    response = client.get("/me")
    assert response.status_code == 500


def test_get_chats(mock_telegram_service):
    mock_telegram_service.get_chats = AsyncMock(return_value=[{"id": 1}])
    response = client.get("/chats")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_chat(mock_telegram_service):
    mock_telegram_service.get_chat = AsyncMock(return_value={"id": 123})
    response = client.get("/chats/123")
    assert response.status_code == 200
    assert response.json()["id"] == 123


def test_get_messages(mock_telegram_service):
    mock_telegram_service.get_messages = AsyncMock(return_value=[])
    response = client.get("/chats/123/messages")
    assert response.status_code == 200


def test_send_message(mock_telegram_service):
    mock_telegram_service.send_message = AsyncMock(return_value={"id": 1})
    response = client.post("/chats/123/messages", json={"message": "Hi"})
    assert response.status_code == 200


def test_schedule_message(mock_telegram_service):
    mock_telegram_service.schedule_message = AsyncMock(return_value={"id": 1})
    response = client.post("/chats/123/schedule", json={"message": "Hi", "minutes_from_now": 10})
    assert response.status_code == 200


def test_send_file(mock_telegram_service):
    mock_telegram_service.send_file = AsyncMock(return_value={"id": 1})
    response = client.post("/chats/123/files", files={"file": ("test.txt", b"content")})
    assert response.status_code == 200


def test_get_contacts(mock_telegram_service):
    mock_telegram_service.get_contacts = AsyncMock(return_value=[])
    response = client.get("/contacts")
    assert response.status_code == 200


def test_search_contacts(mock_telegram_service):
    mock_telegram_service.search_contacts = AsyncMock(return_value=[])
    response = client.get("/contacts/search?query=test")
    assert response.status_code == 200


def test_get_history(mock_telegram_service):
    mock_telegram_service.get_messages = AsyncMock(return_value=[])
    response = client.get("/chats/123/history")
    assert response.status_code == 200


def test_send_reaction(mock_telegram_service):
    mock_telegram_service.send_reaction = AsyncMock(return_value=True)
    response = client.post("/chats/123/messages/1/reaction", json={"emoji": "👍"})
    assert response.status_code == 200


def test_reply_to_message(mock_telegram_service):
    mock_telegram_service.send_message = AsyncMock(return_value={})
    response = client.post("/chats/123/messages/1/reply", json={"message": "Reply"})
    assert response.status_code == 200


def test_edit_message(mock_telegram_service):
    mock_telegram_service.edit_message = AsyncMock(return_value={})
    response = client.put("/chats/123/messages/1", json={"new_text": "Edited"})
    assert response.status_code == 200


def test_delete_message(mock_telegram_service):
    mock_telegram_service.delete_message = AsyncMock(return_value={})
    response = client.delete("/chats/123/messages/1")
    assert response.status_code == 200


def test_forward_message(mock_telegram_service):
    mock_telegram_service.forward_message = AsyncMock(return_value={})
    response = client.post("/chats/123/messages/1/forward?to_chat_id=456")
    assert response.status_code == 200


def test_mark_as_read(mock_telegram_service):
    mock_telegram_service.mark_as_read = AsyncMock(return_value={})
    response = client.post("/chats/123/read")
    assert response.status_code == 200


def test_pin_message(mock_telegram_service):
    mock_telegram_service.pin_message = AsyncMock(return_value={})
    response = client.post("/chats/123/messages/1/pin")
    assert response.status_code == 200


def test_search_messages(mock_telegram_service):
    mock_telegram_service.search_messages = AsyncMock(return_value=[])
    response = client.get("/chats/123/search?query=test")
    assert response.status_code == 200


def test_get_user_status(mock_telegram_service):
    mock_telegram_service.get_user_status = AsyncMock(return_value={})
    response = client.get("/users/123/status")
    assert response.status_code == 200


def test_get_user_photos(mock_telegram_service):
    mock_telegram_service.get_user_photos = AsyncMock(return_value=[])
    response = client.get("/users/123/photos")
    assert response.status_code == 200


def test_search_gifs(mock_telegram_service):
    mock_telegram_service.search_gifs = AsyncMock(return_value=[])
    response = client.get("/gifs/search?query=fun")
    assert response.status_code == 200
