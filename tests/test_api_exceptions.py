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


def test_api_exceptions(mock_telegram_service):
    # Setup all methods to raise Exception
    methods = [
        "get_me",
        "get_chats",
        "get_chat",
        "get_messages",
        "send_message",
        "schedule_message",
        "send_file",
        "get_contacts",
        "search_contacts",
        "send_reaction",
        "reply_to_message",
        "edit_message",
        "delete_message",
        "forward_message",
        "mark_as_read",
        "pin_message",
        "search_messages",
        "get_user_status",
        "get_user_photos",
        "search_gifs",
    ]

    for method in methods:
        setattr(
            mock_telegram_service,
            method,
            AsyncMock(side_effect=Exception("API Error")),
        )

    # Call all endpoints
    assert client.get("/me").status_code == 500
    assert client.get("/chats").status_code == 500
    assert client.get("/chats/1").status_code == 500
    assert client.get("/chats/1/messages").status_code == 500
    assert (
        client.post("/chats/1/messages", json={"message": "hi"}).status_code
        == 500
    )
    assert (
        client.post(
            "/chats/1/schedule", json={"message": "hi", "minutes_from_now": 1}
        ).status_code
        == 500
    )
    assert (
        client.post("/chats/1/files", files={"file": b"c"}).status_code == 500
    )
    assert client.get("/contacts").status_code == 500
    assert client.get("/contacts/search?query=q").status_code == 500
    assert client.get("/chats/1/history").status_code == 500
    assert (
        client.post(
            "/chats/1/messages/1/reaction", json={"emoji": "e"}
        ).status_code
        == 500
    )
    assert (
        client.post(
            "/chats/1/messages/1/reply", json={"message": "r"}
        ).status_code
        == 500
    )
    assert (
        client.put("/chats/1/messages/1", json={"new_text": "e"}).status_code
        == 500
    )
    assert client.delete("/chats/1/messages/1").status_code == 500
    assert (
        client.post("/chats/1/messages/1/forward?to_chat_id=2").status_code
        == 500
    )
    assert client.post("/chats/1/read").status_code == 500
    assert client.post("/chats/1/messages/1/pin").status_code == 500
    assert client.get("/chats/1/search?query=q").status_code == 500
    assert client.get("/users/1/status").status_code == 500
    assert client.get("/users/1/photos").status_code == 500
    assert client.get("/gifs/search?query=q").status_code == 500
