import random
from datetime import datetime
from telethon import functions
from telethon.tl.types import InputMediaPoll, Poll, PollAnswer, TextWithEntities
from backend.client import client
from backend.utils import log_and_format_error

async def create_poll(chat_id: int, question: str, options: list, multiple_choice: bool = False, quiz_mode: bool = False, public_votes: bool = True, close_date: str = None) -> str:
    try:
        entity = await client.get_entity(chat_id)
        if len(options) < 2: return "Error: Poll must have at least 2 options."
        if len(options) > 10: return "Error: Poll can have at most 10 options."

        close_date_obj = None
        if close_date:
            try:
                close_date_obj = datetime.fromisoformat(close_date.replace("Z", "+00:00"))
            except ValueError:
                return f"Invalid close_date format. Use YYYY-MM-DD HH:MM:SS format."

        poll = Poll(
            id=random.randint(0, 2**63 - 1),
            question=TextWithEntities(text=question, entities=[]),
            answers=[PollAnswer(text=TextWithEntities(text=option, entities=[]), option=bytes([i])) for i, option in enumerate(options)],
            multiple_choice=multiple_choice,
            quiz=quiz_mode,
            public_voters=public_votes,
            close_date=close_date_obj
        )

        await client(functions.messages.SendMediaRequest(peer=entity, media=InputMediaPoll(poll=poll), message="", random_id=random.randint(0, 2**63 - 1)))
        return f"Poll created successfully in chat {chat_id}."
    except Exception as e:
        return log_and_format_error("create_poll", e, chat_id=chat_id)
