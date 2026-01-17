from typing import Optional, List, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field

class SendMessageRequest(BaseModel):
    message: str
    reply_to: Optional[int] = None

class ScheduleMessageRequest(BaseModel):
    message: str
    minutes_from_now: int = Field(..., ge=1, le=525600)

class SendFileRequest(BaseModel):
    caption: Optional[str] = None

class ReactionRequest(BaseModel):
    emoji: str
    big: bool = False

class EditMessageRequest(BaseModel):
    new_text: str

class ChatResponse(BaseModel):
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    unread_count: Optional[int] = None
    last_message: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    date: Optional[str]
    text: Optional[str]
    out: bool
    sender_name: str
    sender_id: Optional[int]
    reply_to_msg_id: Optional[int] = None
    has_media: bool
    media_type: Optional[str] = None
