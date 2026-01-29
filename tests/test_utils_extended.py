import pytest
from unittest.mock import MagicMock
from backend.utils import (
    json_serializer,
    log_and_format_error,
    ErrorCategory,
    format_entity,
    get_sender_name,
)
from datetime import datetime
from telethon.tl.types import Chat, User


def test_json_serializer_datetime():
    dt = datetime(2024, 1, 1, 12, 0, 0)
    assert json_serializer(dt) == "2024-01-01T12:00:00"


def test_json_serializer_bytes():
    b = b"hello"
    assert json_serializer(b) == "hello"


def test_json_serializer_error():
    with pytest.raises(TypeError):
        json_serializer(object())


def test_log_and_format_error_validation_prefix():
    msg = log_and_format_error("func", Exception("e"), prefix="VALIDATION-001")
    assert "(code: VALIDATION-001)" in msg


def test_log_and_format_error_category_prefix():
    msg = log_and_format_error(
        "func", Exception("e"), prefix=ErrorCategory.CHAT
    )
    assert "CHAT-ERR" in msg


def test_log_and_format_error_auto_category():
    msg = log_and_format_error("get_chat", Exception("e"))
    assert "CHAT-ERR" in msg


def test_log_and_format_error_user_message():
    msg = log_and_format_error("func", Exception("e"), user_message="User Msg")
    assert msg == "User Msg"


def test_format_entity_chat():
    e = MagicMock(spec=Chat)
    e.id = 123
    e.title = "Group"
    res = format_entity(e)
    assert res["id"] == 123
    assert res["name"] == "Group"
    assert res["type"] == "group"


def test_format_entity_user():
    e = MagicMock(spec=User)
    e.id = 456
    e.first_name = "Alice"
    e.last_name = "Doe"
    e.username = "alice"
    e.phone = "123"
    # Need to remove title attr if it exists on mock
    del e.title

    res = format_entity(e)
    assert res["id"] == 456
    assert res["name"] == "Alice Doe"
    assert res["type"] == "user"
    assert res["username"] == "alice"
    assert res["phone"] == "123"


def test_get_sender_name_title():
    m = MagicMock()
    m.sender.title = "Group Name"
    assert get_sender_name(m) == "Group Name"


def test_get_sender_name_user():
    m = MagicMock()
    del m.sender.title  # Ensure no title
    m.sender.first_name = "Bob"
    m.sender.last_name = None
    assert get_sender_name(m) == "Bob"


def test_get_sender_name_unknown():
    m = MagicMock()
    m.sender = None
    assert get_sender_name(m) == "Unknown"
