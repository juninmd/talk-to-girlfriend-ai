from typing import Union
from telethon import functions
from telethon.tl.types import ReactionEmoji, ReactionCustomEmoji
from backend.client import client
from backend.utils import log_and_format_error, validate_id, json_serializer
import json


@validate_id("chat_id")
async def send_reaction(
    chat_id: Union[int, str], message_id: int, emoji: str, big: bool = False
) -> str:
    try:
        peer = await client.get_input_entity(chat_id)
        await client(
            functions.messages.SendReactionRequest(
                peer=peer, msg_id=message_id, big=big, reaction=[ReactionEmoji(emoticon=emoji)]
            )
        )
        return f"Reaction '{emoji}' sent to message {message_id} in chat {chat_id}."
    except Exception as e:
        return log_and_format_error("send_reaction", e, chat_id=chat_id)


@validate_id("chat_id")
async def remove_reaction(chat_id: Union[int, str], message_id: int) -> str:
    try:
        peer = await client.get_input_entity(chat_id)
        await client(
            functions.messages.SendReactionRequest(peer=peer, msg_id=message_id, reaction=[])
        )
        return f"Reaction removed from message {message_id}."
    except Exception as e:
        return log_and_format_error("remove_reaction", e, chat_id=chat_id)


@validate_id("chat_id")
async def get_message_reactions(chat_id: Union[int, str], message_id: int, limit: int = 50) -> str:
    try:
        peer = await client.get_input_entity(chat_id)
        result = await client(
            functions.messages.GetMessageReactionsListRequest(
                peer=peer, id=message_id, limit=limit
            )
        )
        if not result.reactions:
            return f"No reactions on message {message_id}."

        data = []
        for r in result.reactions:
            user_id = r.peer_id.user_id if hasattr(r.peer_id, "user_id") else None
            emoji = (
                r.reaction.emoticon
                if isinstance(r.reaction, ReactionEmoji)
                else f"custom:{r.reaction.document_id}"
            )
            data.append(
                {
                    "user_id": user_id,
                    "emoji": emoji,
                    "date": r.date.isoformat() if r.date else None,
                }
            )

        return json.dumps({"reactions": data}, indent=2, default=json_serializer)
    except Exception as e:
        return log_and_format_error("get_message_reactions", e, chat_id=chat_id)
