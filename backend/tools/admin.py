from typing import Union, List, Optional
from telethon import functions
from telethon.tl.types import (
    ChatAdminRights,
    ChatBannedRights,
    ChannelParticipantsAdmins,
    ChannelParticipantsKicked,
)
from telethon.errors import rpcerrorlist
from backend.client import client
from backend.utils import log_and_format_error, validate_id, format_entity, json_serializer
import json


@validate_id("group_id", "user_id")
async def promote_admin(
    group_id: Union[int, str], user_id: Union[int, str], rights: dict = None
) -> str:
    try:
        chat = await client.get_entity(group_id)
        user = await client.get_entity(user_id)
        if not rights:
            rights = {
                "change_info": True,
                "post_messages": True,
                "edit_messages": True,
                "delete_messages": True,
                "ban_users": True,
                "invite_users": True,
                "pin_messages": True,
                "add_admins": False,
                "anonymous": False,
                "manage_call": True,
                "other": True,
            }
        admin_rights = ChatAdminRights(
            **{k: v for k, v in rights.items() if hasattr(ChatAdminRights, k)}
        )

        try:
            await client(
                functions.channels.EditAdminRequest(
                    channel=chat, user_id=user, admin_rights=admin_rights, rank="Admin"
                )
            )
            return f"Successfully promoted user {user_id} to admin in {chat.title}"
        except rpcerrorlist.UserNotMutualContactError:
            return "Error: Cannot promote users who are not mutual contacts."
    except Exception as e:
        return log_and_format_error("promote_admin", e, group_id=group_id, user_id=user_id)


@validate_id("group_id", "user_id")
async def demote_admin(group_id: Union[int, str], user_id: Union[int, str]) -> str:
    try:
        chat = await client.get_entity(group_id)
        user = await client.get_entity(user_id)
        admin_rights = ChatAdminRights(
            change_info=False,
            post_messages=False,
            edit_messages=False,
            delete_messages=False,
            ban_users=False,
            invite_users=False,
            pin_messages=False,
            add_admins=False,
            anonymous=False,
            manage_call=False,
            other=False,
        )
        try:
            await client(
                functions.channels.EditAdminRequest(
                    channel=chat, user_id=user, admin_rights=admin_rights, rank=""
                )
            )
            return f"Successfully demoted user {user_id}."
        except rpcerrorlist.UserNotMutualContactError:
            return "Error: Cannot modify admin status of users who are not mutual contacts."
    except Exception as e:
        return log_and_format_error("demote_admin", e, group_id=group_id, user_id=user_id)


@validate_id("chat_id", "user_id")
async def ban_user(chat_id: Union[int, str], user_id: Union[int, str]) -> str:
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        banned_rights = ChatBannedRights(
            until_date=None,
            view_messages=True,
            send_messages=True,
            send_media=True,
            send_stickers=True,
            send_gifs=True,
            send_games=True,
            send_inline=True,
            embed_links=True,
            send_polls=True,
            change_info=True,
            invite_users=True,
            pin_messages=True,
        )
        try:
            await client(
                functions.channels.EditBannedRequest(
                    channel=chat, participant=user, banned_rights=banned_rights
                )
            )
            return f"User {user_id} banned from chat {chat.title}."
        except rpcerrorlist.UserNotMutualContactError:
            return "Error: Cannot ban users who are not mutual contacts."
    except Exception as e:
        return log_and_format_error("ban_user", e, chat_id=chat_id, user_id=user_id)


@validate_id("chat_id", "user_id")
async def unban_user(chat_id: Union[int, str], user_id: Union[int, str]) -> str:
    try:
        chat = await client.get_entity(chat_id)
        user = await client.get_entity(user_id)
        unbanned_rights = ChatBannedRights(
            until_date=None,
            view_messages=False,
            send_messages=False,
            send_media=False,
            send_stickers=False,
            send_gifs=False,
            send_games=False,
            send_inline=False,
            embed_links=False,
            send_polls=False,
            change_info=False,
            invite_users=False,
            pin_messages=False,
        )
        try:
            await client(
                functions.channels.EditBannedRequest(
                    channel=chat, participant=user, banned_rights=unbanned_rights
                )
            )
            return f"User {user_id} unbanned."
        except rpcerrorlist.UserNotMutualContactError:
            return "Error: Cannot modify status of users who are not mutual contacts."
    except Exception as e:
        return log_and_format_error("unban_user", e, chat_id=chat_id, user_id=user_id)


@validate_id("chat_id")
async def get_admins(chat_id: Union[int, str]) -> str:
    try:
        participants = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins())
        lines = [
            f"ID: {p.id}, Name: {getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}".strip()
            for p in participants
        ]
        return "\n".join(lines) if lines else "No admins found."
    except Exception as e:
        return log_and_format_error("get_admins", e, chat_id=chat_id)


@validate_id("chat_id")
async def get_banned_users(chat_id: Union[int, str]) -> str:
    try:
        participants = await client.get_participants(
            chat_id, filter=ChannelParticipantsKicked(q="")
        )
        lines = [
            f"ID: {p.id}, Name: {getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}".strip()
            for p in participants
        ]
        return "\n".join(lines) if lines else "No banned users found."
    except Exception as e:
        return log_and_format_error("get_banned_users", e, chat_id=chat_id)


@validate_id("chat_id")
async def get_recent_actions(chat_id: Union[int, str]) -> str:
    try:
        result = await client(
            functions.channels.GetAdminLogRequest(
                channel=chat_id, q="", events_filter=None, admins=[], max_id=0, min_id=0, limit=20
            )
        )
        if not result or not result.events:
            return "No recent admin actions found."
        return json.dumps([e.to_dict() for e in result.events], indent=2, default=json_serializer)
    except Exception as e:
        return log_and_format_error("get_recent_actions", e, chat_id=chat_id)
