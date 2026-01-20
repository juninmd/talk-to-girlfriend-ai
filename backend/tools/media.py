from typing import Union
import os
from mimetypes import guess_type
from backend.client import client
from backend.utils import log_and_format_error, validate_id


@validate_id("chat_id")
async def send_file(chat_id: Union[int, str], file_path: str, caption: str = None) -> str:
    try:
        if not os.path.isfile(file_path):
            return f"File not found: {file_path}"
        if not os.access(file_path, os.R_OK):
            return f"File is not readable: {file_path}"
        entity = await client.get_entity(chat_id)
        await client.send_file(entity, file_path, caption=caption)
        return f"File sent to chat {chat_id}."
    except Exception as e:
        return log_and_format_error("send_file", e, chat_id=chat_id, file_path=file_path)


@validate_id("chat_id")
async def download_media(chat_id: Union[int, str], message_id: int, file_path: str) -> str:
    try:
        entity = await client.get_entity(chat_id)
        msg = await client.get_messages(entity, ids=message_id)
        if not msg or not msg.media:
            return "No media found in the specified message."
        dir_path = os.path.dirname(file_path) or "."
        if not os.access(dir_path, os.W_OK):
            return f"Directory not writable: {dir_path}"
        await client.download_media(msg, file=file_path)
        if not os.path.isfile(file_path):
            return f"Download failed."
        return f"Media downloaded to {file_path}."
    except Exception as e:
        return log_and_format_error("download_media", e, chat_id=chat_id)


@validate_id("chat_id")
async def send_voice(chat_id: Union[int, str], file_path: str) -> str:
    try:
        if not os.path.isfile(file_path):
            return f"File not found."
        mime, _ = guess_type(file_path)
        if not (
            mime
            and (
                mime == "audio/ogg"
                or file_path.lower().endswith(".ogg")
                or file_path.lower().endswith(".opus")
            )
        ):
            return "Voice file must be .ogg or .opus format."
        entity = await client.get_entity(chat_id)
        await client.send_file(entity, file_path, voice_note=True)
        return f"Voice message sent."
    except Exception as e:
        return log_and_format_error("send_voice", e, chat_id=chat_id)
