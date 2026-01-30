from typing import Union
import os
import json
from telethon import functions
from telethon.tl.types import InputMessagesFilterGif
from backend.client import client
from backend.utils import log_and_format_error, validate_id, json_serializer


async def get_sticker_sets() -> str:
    try:
        result = await client(functions.messages.GetAllStickersRequest(hash=0))
        return json.dumps([s.title for s in result.sets], indent=2)
    except Exception as e:
        return log_and_format_error("get_sticker_sets", e)


@validate_id("chat_id")
async def send_sticker(chat_id: Union[int, str], file_path: str) -> str:
    try:
        if not os.path.isfile(file_path):
            return f"Sticker file not found: {file_path}"
        if not file_path.lower().endswith(".webp"):
            return "Sticker file must be .webp file."
        entity = await client.get_entity(chat_id)
        await client.send_file(entity, file_path, force_document=False)
        return f"Sticker sent to chat {chat_id}."
    except Exception as e:
        return log_and_format_error("send_sticker", e, chat_id=chat_id)


async def get_gif_search(query: str, limit: int = 10) -> str:
    try:
        try:
            result = await client(
                functions.messages.SearchGifsRequest(q=query, offset_id=0, limit=limit)
            )
            if not result.gifs:
                return "[]"
            return json.dumps(
                [g.document.id for g in result.gifs], indent=2, default=json_serializer
            )
        except Exception:
            result = await client(
                functions.messages.SearchRequest(
                    peer="gif",
                    q=query,
                    filter=InputMessagesFilterGif(),
                    min_date=None,
                    max_date=None,
                    offset_id=0,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0,
                )
            )
            if not result or not hasattr(result, "messages") or not result.messages:
                return "[]"
            gif_ids = []
            for msg in result.messages:
                if hasattr(msg, "media") and msg.media and hasattr(msg.media, "document"):
                    gif_ids.append(msg.media.document.id)
            return json.dumps(gif_ids, default=json_serializer)
    except Exception as e:
        return log_and_format_error("get_gif_search", e, query=query)


@validate_id("chat_id")
async def send_gif(chat_id: Union[int, str], gif_id: int) -> str:
    try:
        if not isinstance(gif_id, int):
            return "gif_id must be an integer (document ID)."
        entity = await client.get_entity(chat_id)
        await client.send_file(entity, gif_id)
        return f"GIF sent to chat {chat_id}."
    except Exception as e:
        return log_and_format_error("send_gif", e, chat_id=chat_id, gif_id=gif_id)
