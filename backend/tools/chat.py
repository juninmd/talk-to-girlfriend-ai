from typing import Union, List
from telethon import functions
from telethon.tl.types import User, Chat, Channel
from backend.client import client
from backend.utils import log_and_format_error, validate_id


async def get_chats(page: int = 1, page_size: int = 20) -> str:
    """
    Get a paginated list of chats.
    Args:
        page: Page number (1-indexed).
        page_size: Number of chats per page.
    """
    try:
        dialogs = await client.get_dialogs()
        start = (page - 1) * page_size
        end = start + page_size
        if start >= len(dialogs):
            return "Page out of range."
        chats = dialogs[start:end]
        lines = []
        for dialog in chats:
            entity = dialog.entity
            chat_id = entity.id
            title = getattr(entity, "title", None) or getattr(
                entity, "first_name", "Unknown"
            )
            lines.append(f"Chat ID: {chat_id}, Title: {title}")
        return "\n".join(lines)
    except Exception as e:
        return log_and_format_error("get_chats", e)


async def list_chats(chat_type: str = None, limit: int = 20) -> str:
    """
    List available chats with metadata.
    Args:
        chat_type: Filter by chat type ('user', 'group', 'channel', or None for all)
        limit: Maximum number of chats to retrieve.
    """
    try:
        dialogs = await client.get_dialogs(limit=limit)
        results = []
        for dialog in dialogs:
            entity = dialog.entity
            current_type = None
            if isinstance(entity, User):
                current_type = "user"
            elif isinstance(entity, Chat):
                current_type = "group"
            elif isinstance(entity, Channel):
                if getattr(entity, "broadcast", False):
                    current_type = "channel"
                else:
                    current_type = "group"  # Supergroup

            if chat_type and current_type != chat_type.lower():
                continue

            chat_info = f"Chat ID: {entity.id}"
            if hasattr(entity, "title"):
                chat_info += f", Title: {entity.title}"
            elif hasattr(entity, "first_name"):
                name = f"{entity.first_name}"
                if hasattr(entity, "last_name") and entity.last_name:
                    name += f" {entity.last_name}"
                chat_info += f", Name: {name}"

            chat_info += f", Type: {current_type}"
            if hasattr(entity, "username") and entity.username:
                chat_info += f", Username: @{entity.username}"

            unread_count = getattr(dialog, "unread_count", 0) or 0
            inner_dialog = getattr(dialog, "dialog", None)
            unread_mark = (
                bool(getattr(inner_dialog, "unread_mark", False))
                if inner_dialog
                else False
            )

            if unread_count > 0:
                chat_info += f", Unread: {unread_count}"
            elif unread_mark:
                chat_info += ", Unread: marked"
            else:
                chat_info += ", No unread messages"

            results.append(chat_info)

        if not results:
            return "No chats found matching the criteria."
        return "\n".join(results)
    except Exception as e:
        return log_and_format_error("list_chats", e, chat_type=chat_type, limit=limit)


@validate_id("chat_id")
async def get_chat(chat_id: Union[int, str]) -> str:
    """
    Get detailed information about a specific chat.
    Args:
        chat_id: The ID or username of the chat.
    """
    try:
        entity = await client.get_entity(chat_id)
        result = []
        result.append(f"ID: {entity.id}")
        is_channel = isinstance(entity, Channel)
        is_chat = isinstance(entity, Chat)
        is_user = isinstance(entity, User)

        if hasattr(entity, "title"):
            result.append(f"Title: {entity.title}")
            chat_type = (
                "Channel"
                if is_channel and getattr(entity, "broadcast", False)
                else "Group"
            )
            if is_channel and getattr(entity, "megagroup", False):
                chat_type = "Supergroup"
            elif is_chat:
                chat_type = "Group (Basic)"
            result.append(f"Type: {chat_type}")
            if hasattr(entity, "username") and entity.username:
                result.append(f"Username: @{entity.username}")
            try:
                participants_count = (
                    await client.get_participants(entity, limit=0)
                ).total
                result.append(f"Participants: {participants_count}")
            except Exception as pe:
                result.append(f"Participants: Error fetching ({pe})")
        elif is_user:
            name = f"{entity.first_name}"
            if entity.last_name:
                name += f" {entity.last_name}"
            result.append(f"Name: {name}")
            result.append("Type: User")
            if entity.username:
                result.append(f"Username: @{entity.username}")
            if entity.phone:
                result.append(f"Phone: {entity.phone}")
            result.append(f"Bot: {'Yes' if entity.bot else 'No'}")
            result.append(f"Verified: {'Yes' if entity.verified else 'No'}")

        return "\n".join(result)
    except Exception as e:
        return log_and_format_error("get_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def leave_chat(chat_id: Union[int, str]) -> str:
    """
    Leave a group or channel by chat ID.
    Args:
        chat_id: The chat ID or username to leave.
    """
    try:
        entity = await client.get_entity(chat_id)
        if isinstance(entity, Channel):
            try:
                await client(functions.channels.LeaveChannelRequest(channel=entity))
                chat_name = getattr(entity, "title", str(chat_id))
                return f"Left channel/supergroup {chat_name} (ID: {chat_id})."
            except Exception as chan_err:
                return log_and_format_error("leave_chat", chan_err, chat_id=chat_id)
        elif isinstance(entity, Chat):
            try:
                me = await client.get_me(input_peer=True)
                await client(
                    functions.messages.DeleteChatUserRequest(
                        chat_id=entity.id, user_id=me
                    )
                )
                chat_name = getattr(entity, "title", str(chat_id))
                return f"Left basic group {chat_name} (ID: {chat_id})."
            except Exception:
                try:
                    me_full = await client.get_me()
                    await client(
                        functions.messages.DeleteChatUserRequest(
                            chat_id=entity.id, user_id=me_full.id
                        )
                    )
                    chat_name = getattr(entity, "title", str(chat_id))
                    return f"Left basic group {chat_name} (ID: {chat_id})."
                except Exception as alt_err:
                    return log_and_format_error("leave_chat", alt_err, chat_id=chat_id)
        else:
            return log_and_format_error(
                "leave_chat",
                Exception(
                    f"Cannot leave chat ID {chat_id} of type {type(entity).__name__}."
                ),
                chat_id=chat_id,
            )
    except Exception as e:
        return log_and_format_error("leave_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def get_invite_link(chat_id: Union[int, str]) -> str:
    try:
        entity = await client.get_entity(chat_id)
        try:
            result = await client(
                functions.messages.ExportChatInviteRequest(peer=entity)
            )
            return result.link
        except Exception:
            pass
        try:
            invite_link = await client.export_chat_invite_link(entity)
            return invite_link
        except Exception:
            pass
        return "Could not retrieve invite link."
    except Exception as e:
        return log_and_format_error("get_invite_link", e, chat_id=chat_id)


async def join_chat_by_link(link: str) -> str:
    try:
        if "/" in link:
            hash_part = link.split("/")[-1]
            if hash_part.startswith("+"):
                hash_part = hash_part[1:]
        else:
            hash_part = link

        result = await client(
            functions.messages.ImportChatInviteRequest(hash=hash_part)
        )
        if result and hasattr(result, "chats") and result.chats:
            chat_title = getattr(result.chats[0], "title", "Unknown Chat")
            return f"Successfully joined chat: {chat_title}"
        return "Joined chat via invite hash."
    except Exception as e:
        return log_and_format_error("join_chat_by_link", e, link=link)


async def create_group(title: str, user_ids: List[Union[int, str]]) -> str:
    try:
        users = []
        for user_id in user_ids:
            try:
                users.append(await client.get_entity(user_id))
            except Exception:
                pass
        if not users:
            return "Error: No valid users provided"
        result = await client(
            functions.messages.CreateChatRequest(users=users, title=title)
        )
        if hasattr(result, "chats") and result.chats:
            return f"Group created with ID: {result.chats[0].id}"
        return "Group created."
    except Exception as e:
        return log_and_format_error("create_group", e, title=title)


@validate_id("chat_id")
async def mute_chat(chat_id: Union[int, str]) -> str:
    try:
        from telethon.tl.types import InputPeerNotifySettings

        peer = await client.get_input_entity(chat_id)
        await client(
            functions.account.UpdateNotifySettingsRequest(
                peer=peer, settings=InputPeerNotifySettings(mute_until=2**31 - 1)
            )
        )
        return f"Chat {chat_id} muted."
    except Exception as e:
        return log_and_format_error("mute_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def unmute_chat(chat_id: Union[int, str]) -> str:
    try:
        from telethon.tl.types import InputPeerNotifySettings

        peer = await client.get_input_entity(chat_id)
        await client(
            functions.account.UpdateNotifySettingsRequest(
                peer=peer, settings=InputPeerNotifySettings(mute_until=0)
            )
        )
        return f"Chat {chat_id} unmuted."
    except Exception as e:
        return log_and_format_error("unmute_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def archive_chat(chat_id: Union[int, str]) -> str:
    try:
        await client(
            functions.messages.ToggleDialogPinRequest(
                peer=await client.get_entity(chat_id), pinned=True
            )
        )
        return f"Chat {chat_id} archived."
    except Exception as e:
        return log_and_format_error("archive_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def unarchive_chat(chat_id: Union[int, str]) -> str:
    try:
        await client(
            functions.messages.ToggleDialogPinRequest(
                peer=await client.get_entity(chat_id), pinned=False
            )
        )
        return f"Chat {chat_id} unarchived."
    except Exception as e:
        return log_and_format_error("unarchive_chat", e, chat_id=chat_id)


@validate_id("chat_id")
async def edit_chat_title(chat_id: Union[int, str], title: str) -> str:
    try:
        entity = await client.get_entity(chat_id)
        if isinstance(entity, Channel):
            await client(
                functions.channels.EditTitleRequest(channel=entity, title=title)
            )
        elif isinstance(entity, Chat):
            await client(
                functions.messages.EditChatTitleRequest(chat_id=chat_id, title=title)
            )
        else:
            return "Cannot edit title for this entity."
        return f"Chat {chat_id} title updated to '{title}'."
    except Exception as e:
        return log_and_format_error("edit_chat_title", e, chat_id=chat_id)


@validate_id("chat_id")
async def edit_chat_photo(chat_id: Union[int, str], file_path: str) -> str:
    try:
        from telethon.tl.types import InputChatUploadedPhoto

        entity = await client.get_entity(chat_id)
        uploaded = await client.upload_file(file_path)
        if isinstance(entity, Channel):
            await client(
                functions.channels.EditPhotoRequest(
                    channel=entity, photo=InputChatUploadedPhoto(file=uploaded)
                )
            )
        elif isinstance(entity, Chat):
            await client(
                functions.messages.EditChatPhotoRequest(
                    chat_id=chat_id, photo=InputChatUploadedPhoto(file=uploaded)
                )
            )
        return f"Chat {chat_id} photo updated."
    except Exception as e:
        return log_and_format_error("edit_chat_photo", e, chat_id=chat_id)


@validate_id("chat_id")
async def delete_chat_photo(chat_id: Union[int, str]) -> str:
    try:
        from telethon.tl.types import InputChatPhotoEmpty

        entity = await client.get_entity(chat_id)
        if isinstance(entity, Channel):
            await client(
                functions.channels.EditPhotoRequest(
                    channel=entity, photo=InputChatPhotoEmpty()
                )
            )
        elif isinstance(entity, Chat):
            await client(
                functions.messages.EditChatPhotoRequest(
                    chat_id=chat_id, photo=InputChatPhotoEmpty()
                )
            )
        return f"Chat {chat_id} photo deleted."
    except Exception as e:
        return log_and_format_error("delete_chat_photo", e, chat_id=chat_id)
