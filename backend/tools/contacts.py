from typing import Union, List
from telethon import functions
from backend.client import client
from backend.utils import log_and_format_error, validate_id

async def list_contacts() -> str:
    try:
        result = await client(functions.contacts.GetContactsRequest(hash=0))
        users = result.users
        if not users: return "No contacts found."
        lines = []
        for user in users:
            name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            username = getattr(user, 'username', '')
            phone = getattr(user, 'phone', '')
            info = f"ID: {user.id}, Name: {name}"
            if username: info += f", Username: @{username}"
            if phone: info += f", Phone: {phone}"
            lines.append(info)
        return "\n".join(lines)
    except Exception as e:
        return log_and_format_error("list_contacts", e)

async def search_contacts(query: str) -> str:
    try:
        result = await client(functions.contacts.SearchRequest(q=query, limit=50))
        users = result.users
        if not users: return f"No contacts found matching '{query}'."
        lines = []
        for user in users:
            name = f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
            username = getattr(user, 'username', '')
            info = f"ID: {user.id}, Name: {name}"
            if username: info += f", Username: @{username}"
            lines.append(info)
        return "\n".join(lines)
    except Exception as e:
        return log_and_format_error("search_contacts", e, query=query)

async def add_contact(phone: str, first_name: str, last_name: str = "") -> str:
    try:
        from telethon.tl.types import InputPhoneContact
        result = await client(functions.contacts.ImportContactsRequest(
            contacts=[InputPhoneContact(client_id=0, phone=phone, first_name=first_name, last_name=last_name)]
        ))
        if result.imported:
            return f"Contact {first_name} {last_name} added successfully."
        else:
            return f"Contact not added. Response: {str(result)}"
    except Exception as e:
        return log_and_format_error("add_contact", e, phone=phone)

@validate_id("user_id")
async def delete_contact(user_id: Union[int, str]) -> str:
    try:
        user = await client.get_entity(user_id)
        await client(functions.contacts.DeleteContactsRequest(id=[user]))
        return f"Contact with user ID {user_id} deleted."
    except Exception as e:
        return log_and_format_error("delete_contact", e, user_id=user_id)
