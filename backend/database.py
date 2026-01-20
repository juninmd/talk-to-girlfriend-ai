from typing import Optional
from datetime import datetime, timezone
import os
from sqlmodel import SQLModel, Field, create_engine, Session

# Database setup
# Use absolute path for database to avoid issues when running from different directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sqlite_file_name = os.path.join(BASE_DIR, "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_message_id: int
    chat_id: int
    sender_id: Optional[int]
    sender_name: Optional[str]
    text: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_outgoing: bool


class Fact(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int
    entity_name: str  # e.g., "User's Name", "Favorite Color"
    value: str
    category: str = "general"  # personal, work, preference, etc.
    source_message_id: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
