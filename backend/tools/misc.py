from typing import Union
from backend.client import client
from backend.utils import log_and_format_error, validate_id, format_entity
import json


async def get_me() -> str:
    try:
        me = await client.get_me()
        return json.dumps(format_entity(me), indent=2)
    except Exception as e:
        return log_and_format_error("get_me", e)


@validate_id("chat_id")
async def get_participants(chat_id: Union[int, str]) -> str:
    try:
        participants = await client.get_participants(chat_id)
        lines = [
            f"ID: {p.id}, Name: {getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}"
            for p in participants
        ]
        return "\n".join(lines)
    except Exception as e:
        return log_and_format_error("get_participants", e, chat_id=chat_id)
