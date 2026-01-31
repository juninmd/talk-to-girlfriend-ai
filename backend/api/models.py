from typing import Union, Any, Optional
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    message: str
    reply_to: Optional[int] = None


class ScheduleMessageRequest(BaseModel):
    message: str
    minutes_from_now: int


class SendFileRequest(BaseModel):
    chat_id: Union[int, str]
    caption: Optional[str] = None
    voice_note: bool = False


class ReactionRequest(BaseModel):
    emoji: str
    big: bool = False


class EditMessageRequest(BaseModel):
    new_text: str


class Chat(BaseModel):
    id: int
    title: Optional[str] = None
    username: Optional[str] = None
    type: str


class Message(BaseModel):
    id: int
    date: Optional[str] = None
    text: Optional[str] = None
    sender_id: Optional[int] = None
    sender_name: Optional[str] = "Unknown"
    reply_to_msg_id: Optional[int] = None
    media: Optional[Any] = None
