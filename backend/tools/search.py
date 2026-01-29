from telethon import functions
from backend.client import client
from backend.utils import log_and_format_error, format_entity
import json


async def search_public_chats(query: str) -> str:
    try:
        result = await client(
            functions.contacts.SearchRequest(q=query, limit=20)
        )
        return json.dumps([format_entity(u) for u in result.users], indent=2)
    except Exception as e:
        return log_and_format_error("search_public_chats", e, query=query)


async def resolve_username(username: str) -> str:
    try:
        result = await client(
            functions.contacts.ResolveUsernameRequest(username=username)
        )
        return str(result)
    except Exception as e:
        return log_and_format_error("resolve_username", e, username=username)
