from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional, Union
from backend.services.telegram import TelegramService
from backend.api.models import (
    SendMessageRequest,
    ScheduleMessageRequest,
    ReactionRequest,
    EditMessageRequest,
)

router = APIRouter()


@router.get("/health")
async def health_check():
    from backend.client import client

    return {"status": "ok", "connected": client.is_connected()}


@router.get("/me")
async def get_me():
    try:
        return await TelegramService.get_me()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats")
async def get_chats(limit: int = 20, type: Optional[str] = None):
    try:
        return await TelegramService.get_chats(limit=limit, chat_type=type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}")
async def get_chat(chat_id: Union[int, str]):
    try:
        return await TelegramService.get_chat(chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/messages")
async def get_messages(chat_id: Union[int, str], limit: int = 20, offset_id: Optional[int] = None):
    try:
        return await TelegramService.get_messages(chat_id, limit, offset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages")
async def send_message(chat_id: Union[int, str], request: SendMessageRequest):
    try:
        return await TelegramService.send_message(chat_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/schedule")
async def schedule_message(chat_id: Union[int, str], request: ScheduleMessageRequest):
    try:
        return await TelegramService.schedule_message(chat_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/files")
async def send_file(
    chat_id: Union[int, str],
    file: UploadFile = File(...),
    caption: Optional[str] = None,
    voice_note: bool = False,
):
    try:
        content = await file.read()
        return await TelegramService.send_file(
            chat_id, content, file.filename, caption, voice_note
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts")
async def get_contacts():
    try:
        return await TelegramService.get_contacts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/search")
async def search_contacts(query: str):
    try:
        return await TelegramService.search_contacts(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Extended Endpoints


@router.get("/chats/{chat_id}/history")
async def get_history(chat_id: Union[int, str], limit: int = 50, offset_id: Optional[int] = None):
    try:
        return await TelegramService.get_messages(chat_id, limit, offset_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages/{message_id}/reaction")
async def send_reaction(chat_id: Union[int, str], message_id: int, request: ReactionRequest):
    try:
        return await TelegramService.send_reaction(chat_id, message_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages/{message_id}/reply")
async def reply_to_message(chat_id: Union[int, str], message_id: int, request: SendMessageRequest):
    try:
        request.reply_to = message_id
        return await TelegramService.send_message(chat_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chats/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: Union[int, str], message_id: int, request: EditMessageRequest):
    try:
        return await TelegramService.edit_message(chat_id, message_id, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chats/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: Union[int, str], message_id: int):
    try:
        return await TelegramService.delete_message(chat_id, message_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages/{message_id}/forward")
async def forward_message(chat_id: Union[int, str], message_id: int, to_chat_id: Union[int, str]):
    try:
        return await TelegramService.forward_message(chat_id, message_id, to_chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/read")
async def mark_as_read(chat_id: Union[int, str]):
    try:
        return await TelegramService.mark_as_read(chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chats/{chat_id}/messages/{message_id}/pin")
async def pin_message(chat_id: Union[int, str], message_id: int):
    try:
        return await TelegramService.pin_message(chat_id, message_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chats/{chat_id}/search")
async def search_messages(chat_id: Union[int, str], query: str, limit: int = 20):
    try:
        return await TelegramService.search_messages(chat_id, query, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/status")
async def get_user_status(user_id: Union[int, str]):
    try:
        return await TelegramService.get_user_status(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/photos")
async def get_user_photos(user_id: Union[int, str], limit: int = 10):
    try:
        return await TelegramService.get_user_photos(user_id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gifs/search")
async def search_gifs(query: str, limit: int = 10):
    try:
        return await TelegramService.search_gifs(query, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
