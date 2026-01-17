from typing import Dict, Any, Union, Optional
from datetime import datetime, timedelta
import asyncio

from telethon.tl.types import User, Chat, Channel, ReactionEmoji, InputBotInlineMessageID
from telethon import functions
from fastapi import HTTPException, UploadFile

from backend.client import client
from backend.api.models import (
    SendMessageRequest,
    ScheduleMessageRequest,
    ReactionRequest,
    EditMessageRequest
)

def format_entity(entity) -> Dict[str, Any]:
    """Format entity information consistently."""
    result = {"id": entity.id}
    if isinstance(entity, User):
        result["type"] = "user"
        result["first_name"] = getattr(entity, "first_name", None)
        result["last_name"] = getattr(entity, "last_name", None)
        result["username"] = getattr(entity, "username", None)
        result["phone"] = getattr(entity, "phone", None)
    elif isinstance(entity, Chat):
        result["type"] = "chat"
        result["title"] = getattr(entity, "title", None)
    elif isinstance(entity, Channel):
        result["type"] = "channel"
        result["title"] = getattr(entity, "title", None)
        result["username"] = getattr(entity, "username", None)
    return result

def format_message(message) -> Dict[str, Any]:
    """Format message information consistently."""
    result = {
        "id": message.id,
        "date": message.date.isoformat() if message.date else None,
        "text": message.message,
        "out": message.out,
    }

    if message.sender:
        if hasattr(message.sender, "first_name"):
            first = getattr(message.sender, "first_name", "") or ""
            last = getattr(message.sender, "last_name", "") or ""
            result["sender_name"] = f"{first} {last}".strip() or "Unknown"
        elif hasattr(message.sender, "title"):
            result["sender_name"] = message.sender.title
        else:
            result["sender_name"] = "Unknown"
        result["sender_id"] = message.sender.id
    else:
        result["sender_name"] = "Unknown"
        result["sender_id"] = None

    if message.reply_to and message.reply_to.reply_to_msg_id:
        result["reply_to_msg_id"] = message.reply_to.reply_to_msg_id

    if message.media:
        result["has_media"] = True
        result["media_type"] = type(message.media).__name__
    else:
        result["has_media"] = False

    return result

async def get_entity_safe(chat_id: Union[int, str]):
    """Helper to resolve chat_id/username to entity."""
    if isinstance(chat_id, str) and not chat_id.lstrip('-').isdigit():
        return await client.get_entity(chat_id)
    else:
        return await client.get_entity(int(chat_id))

class TelegramService:
    @staticmethod
    async def get_me():
        me = await client.get_me()
        return format_entity(me)

    @staticmethod
    async def get_chats(limit: int, chat_type: Optional[str] = None):
        dialogs = await client.get_dialogs(limit=limit)
        chats = []
        for dialog in dialogs:
            entity = dialog.entity
            chat_info = format_entity(entity)
            chat_info["unread_count"] = dialog.unread_count
            chat_info["last_message"] = dialog.message.message[:100] if dialog.message and dialog.message.message else None

            if chat_type:
                if chat_type == "user" and isinstance(entity, User):
                    chats.append(chat_info)
                elif chat_type == "chat" and isinstance(entity, Chat):
                    chats.append(chat_info)
                elif chat_type == "channel" and isinstance(entity, Channel):
                    chats.append(chat_info)
            else:
                chats.append(chat_info)
        return {"chats": chats, "count": len(chats)}

    @staticmethod
    async def get_chat(chat_id: Union[int, str]):
        entity = await get_entity_safe(chat_id)
        return format_entity(entity)

    @staticmethod
    async def get_messages(chat_id: Union[int, str], limit: int, offset_id: Optional[int] = None):
        entity = await get_entity_safe(chat_id)
        kwargs = {"limit": limit}
        if offset_id:
            kwargs["offset_id"] = offset_id
        messages = await client.get_messages(entity, **kwargs)
        return {
            "messages": [format_message(msg) for msg in messages],
            "count": len(messages)
        }

    @staticmethod
    async def send_message(chat_id: Union[int, str], request: SendMessageRequest):
        entity = await get_entity_safe(chat_id)
        kwargs = {}
        if request.reply_to:
            kwargs["reply_to"] = request.reply_to
        result = await client.send_message(entity, request.message, **kwargs)
        return {
            "success": True,
            "message_id": result.id,
            "date": result.date.isoformat() if result.date else None
        }

    @staticmethod
    async def schedule_message(chat_id: Union[int, str], request: ScheduleMessageRequest):
        entity = await get_entity_safe(chat_id)
        schedule_time = datetime.now() + timedelta(minutes=request.minutes_from_now)
        result = await client.send_message(entity, request.message, schedule=schedule_time)
        return {
            "success": True,
            "message_id": result.id,
            "scheduled_for": schedule_time.isoformat()
        }

    @staticmethod
    async def send_file(chat_id: Union[int, str], file_content: bytes, filename: str, caption: Optional[str], voice_note: bool):
        entity = await get_entity_safe(chat_id)
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            result = await client.send_file(
                entity,
                tmp_path,
                caption=caption,
                voice_note=voice_note
            )
            return {
                "success": True,
                "message_id": result.id,
                "date": result.date.isoformat() if result.date else None
            }
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @staticmethod
    async def get_contacts():
        result = await client(functions.contacts.GetContactsRequest(hash=0))
        contacts = []
        for user in result.users:
            contacts.append({
                "id": user.id,
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "username": getattr(user, "username", None),
                "phone": getattr(user, "phone", None),
            })
        return {"contacts": contacts, "count": len(contacts)}

    @staticmethod
    async def search_contacts(query: str):
        result = await client(functions.contacts.SearchRequest(q=query, limit=20))
        contacts = []
        for user in result.users:
            if isinstance(user, User):
                contacts.append({
                    "id": user.id,
                    "first_name": getattr(user, "first_name", None),
                    "last_name": getattr(user, "last_name", None),
                    "username": getattr(user, "username", None),
                    "phone": getattr(user, "phone", None),
                })
        return {"contacts": contacts, "count": len(contacts)}

    @staticmethod
    async def send_reaction(chat_id: Union[int, str], message_id: int, request: ReactionRequest):
        entity = await get_entity_safe(chat_id)
        await client(functions.messages.SendReactionRequest(
            peer=entity,
            msg_id=message_id,
            big=request.big,
            reaction=[ReactionEmoji(emoticon=request.emoji)]
        ))
        return {"success": True, "emoji": request.emoji}

    @staticmethod
    async def edit_message(chat_id: Union[int, str], message_id: int, request: EditMessageRequest):
        entity = await get_entity_safe(chat_id)
        result = await client.edit_message(entity, message_id, request.new_text)
        return {"success": True, "message_id": result.id}

    @staticmethod
    async def delete_message(chat_id: Union[int, str], message_id: int):
        entity = await get_entity_safe(chat_id)
        await client.delete_messages(entity, [message_id])
        return {"success": True}

    @staticmethod
    async def forward_message(chat_id: Union[int, str], message_id: int, to_chat_id: Union[int, str]):
        from_entity = await get_entity_safe(chat_id)
        to_entity = await get_entity_safe(to_chat_id)
        result = await client.forward_messages(to_entity, message_id, from_entity)
        return {"success": True, "message_id": result.id if hasattr(result, 'id') else None}

    @staticmethod
    async def mark_as_read(chat_id: Union[int, str]):
        entity = await get_entity_safe(chat_id)
        await client.send_read_acknowledge(entity)
        return {"success": True}

    @staticmethod
    async def pin_message(chat_id: Union[int, str], message_id: int):
        entity = await get_entity_safe(chat_id)
        await client.pin_message(entity, message_id)
        return {"success": True}

    @staticmethod
    async def search_messages(chat_id: Union[int, str], query: str, limit: int):
        entity = await get_entity_safe(chat_id)
        messages = await client.get_messages(entity, limit=limit, search=query)
        return {
            "messages": [format_message(msg) for msg in messages],
            "count": len(messages)
        }

    @staticmethod
    async def get_user_status(user_id: Union[int, str]):
        entity = await get_entity_safe(user_id)
        status = getattr(entity, "status", None)
        status_str = type(status).__name__ if status else "Unknown"

        if "Online" in status_str:
            result = "online"
        elif "Recently" in status_str:
            result = "recently"
        elif "LastWeek" in status_str:
            result = "last_week"
        elif "LastMonth" in status_str:
            result = "last_month"
        elif "Offline" in status_str:
            result = "offline"
        else:
            result = status_str.lower()

        return {"user_id": entity.id, "status": result, "raw_status": status_str}

    @staticmethod
    async def get_user_photos(user_id: Union[int, str], limit: int):
        entity = await get_entity_safe(user_id)
        photos = await client.get_profile_photos(entity, limit=limit)
        return {
            "photos": [{"id": p.id, "date": p.date.isoformat() if p.date else None} for p in photos],
            "count": len(photos)
        }

    @staticmethod
    async def search_gifs(query: str, limit: int):
        result = await client.inline_query("@gif", query)
        gifs = []
        for i, r in enumerate(result):
            if i >= limit:
                break
            gifs.append({
                "id": i,
                "title": getattr(r, "title", None),
                "description": getattr(r, "description", None),
            })
        return {"gifs": gifs, "count": len(gifs)}
