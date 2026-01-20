from typing import Union, Optional
from telethon import functions
from backend.client import client
from backend.utils import log_and_format_error, validate_id, json_serializer
import json


@validate_id("chat_id")
async def save_draft(
    chat_id: Union[int, str],
    message: str,
    reply_to_msg_id: Optional[int] = None,
    no_webpage: bool = False,
) -> str:
    try:
        peer = await client.get_input_entity(chat_id)
        reply_to = None
        if reply_to_msg_id:
            from telethon.tl.types import InputReplyToMessage

            reply_to = InputReplyToMessage(reply_to_msg_id=reply_to_msg_id)

        await client(
            functions.messages.SaveDraftRequest(
                peer=peer, message=message, no_webpage=no_webpage, reply_to=reply_to
            )
        )
        return f"Draft saved to chat {chat_id}."
    except Exception as e:
        return log_and_format_error("save_draft", e, chat_id=chat_id)


async def get_drafts() -> str:
    try:
        result = await client(functions.messages.GetAllDraftsRequest())
        drafts_info = []
        if hasattr(result, "updates"):
            for update in result.updates:
                if hasattr(update, "draft") and update.draft:
                    draft = update.draft
                    peer_id = None
                    if hasattr(update, "peer"):
                        peer = update.peer
                        if hasattr(peer, "user_id"):
                            peer_id = peer.user_id
                        elif hasattr(peer, "chat_id"):
                            peer_id = -peer.chat_id
                        elif hasattr(peer, "channel_id"):
                            peer_id = -1000000000000 - peer.channel_id

                    drafts_info.append(
                        {
                            "peer_id": peer_id,
                            "message": getattr(draft, "message", ""),
                            "date": (
                                draft.date.isoformat()
                                if hasattr(draft, "date") and draft.date
                                else None
                            ),
                            "no_webpage": getattr(draft, "no_webpage", False),
                        }
                    )

        if not drafts_info:
            return "No drafts found."
        return json.dumps(
            {"drafts": drafts_info, "count": len(drafts_info)}, indent=2, default=json_serializer
        )
    except Exception as e:
        return log_and_format_error("get_drafts", e)


@validate_id("chat_id")
async def clear_draft(chat_id: Union[int, str]) -> str:
    try:
        peer = await client.get_input_entity(chat_id)
        await client(functions.messages.SaveDraftRequest(peer=peer, message=""))
        return f"Draft cleared from chat {chat_id}."
    except Exception as e:
        return log_and_format_error("clear_draft", e, chat_id=chat_id)
