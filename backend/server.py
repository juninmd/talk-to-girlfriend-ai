import sys
import asyncio
import nest_asyncio
import sqlite3
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from backend.client import client
from backend.utils import log_and_format_error

# Import tools
from backend.tools import chat, contacts, messages, misc, media, profile, admin, schedule, polls, drafts, stickers, bots, reactions, search

mcp = FastMCP("telegram")

# Register Tools
# Chat Tools
mcp.add_tool(chat.get_chats, annotations=ToolAnnotations(title="Get Chats", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(chat.list_chats, annotations=ToolAnnotations(title="List Chats", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(chat.get_chat, annotations=ToolAnnotations(title="Get Chat", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(chat.leave_chat, annotations=ToolAnnotations(title="Leave Chat", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.get_invite_link, annotations=ToolAnnotations(title="Get Invite Link", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(chat.join_chat_by_link, annotations=ToolAnnotations(title="Join Chat By Link", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.create_group, annotations=ToolAnnotations(title="Create Group", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.mute_chat, annotations=ToolAnnotations(title="Mute Chat", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.unmute_chat, annotations=ToolAnnotations(title="Unmute Chat", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.archive_chat, annotations=ToolAnnotations(title="Archive Chat", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.unarchive_chat, annotations=ToolAnnotations(title="Unarchive Chat", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.edit_chat_title, annotations=ToolAnnotations(title="Edit Chat Title", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.edit_chat_photo, annotations=ToolAnnotations(title="Edit Chat Photo", openWorldHint=True, destructiveHint=True))
mcp.add_tool(chat.delete_chat_photo, annotations=ToolAnnotations(title="Delete Chat Photo", openWorldHint=True, destructiveHint=True))

# Contact Tools
mcp.add_tool(contacts.list_contacts, annotations=ToolAnnotations(title="List Contacts", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(contacts.search_contacts, annotations=ToolAnnotations(title="Search Contacts", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(contacts.add_contact, annotations=ToolAnnotations(title="Add Contact", openWorldHint=True, destructiveHint=True))
mcp.add_tool(contacts.delete_contact, annotations=ToolAnnotations(title="Delete Contact", openWorldHint=True, destructiveHint=True))

# Message Tools
mcp.add_tool(messages.get_messages, annotations=ToolAnnotations(title="Get Messages", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(messages.send_message, annotations=ToolAnnotations(title="Send Message", openWorldHint=True, destructiveHint=True))
mcp.add_tool(messages.list_messages, annotations=ToolAnnotations(title="List Messages", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(messages.reply_to_message, annotations=ToolAnnotations(title="Reply To Message", openWorldHint=True, destructiveHint=True))
mcp.add_tool(messages.delete_message, annotations=ToolAnnotations(title="Delete Message", openWorldHint=True, destructiveHint=True))
mcp.add_tool(messages.pin_message, annotations=ToolAnnotations(title="Pin Message", openWorldHint=True, destructiveHint=True))
mcp.add_tool(messages.unpin_message, annotations=ToolAnnotations(title="Unpin Message", openWorldHint=True, destructiveHint=True))

# Media Tools
mcp.add_tool(media.send_file, annotations=ToolAnnotations(title="Send File", openWorldHint=True, destructiveHint=True))
mcp.add_tool(media.download_media, annotations=ToolAnnotations(title="Download Media", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(media.send_voice, annotations=ToolAnnotations(title="Send Voice", openWorldHint=True, destructiveHint=True))

# Profile Tools
mcp.add_tool(profile.update_profile, annotations=ToolAnnotations(title="Update Profile", openWorldHint=True, destructiveHint=True))
mcp.add_tool(profile.set_profile_photo, annotations=ToolAnnotations(title="Set Profile Photo", openWorldHint=True, destructiveHint=True))

# Admin Tools
mcp.add_tool(admin.promote_admin, annotations=ToolAnnotations(title="Promote Admin", openWorldHint=True, destructiveHint=True))
mcp.add_tool(admin.demote_admin, annotations=ToolAnnotations(title="Demote Admin", openWorldHint=True, destructiveHint=True))
mcp.add_tool(admin.ban_user, annotations=ToolAnnotations(title="Ban User", openWorldHint=True, destructiveHint=True))
mcp.add_tool(admin.unban_user, annotations=ToolAnnotations(title="Unban User", openWorldHint=True, destructiveHint=True))
mcp.add_tool(admin.get_admins, annotations=ToolAnnotations(title="Get Admins", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(admin.get_banned_users, annotations=ToolAnnotations(title="Get Banned Users", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(admin.get_recent_actions, annotations=ToolAnnotations(title="Get Recent Actions", openWorldHint=True, readOnlyHint=True))

# Schedule Tools
mcp.add_tool(schedule.schedule_message, annotations=ToolAnnotations(title="Schedule Message", openWorldHint=True, destructiveHint=True))

# Polls Tools
mcp.add_tool(polls.create_poll, annotations=ToolAnnotations(title="Create Poll", openWorldHint=True, destructiveHint=True))

# Drafts Tools
mcp.add_tool(drafts.save_draft, annotations=ToolAnnotations(title="Save Draft", openWorldHint=True, destructiveHint=True))
mcp.add_tool(drafts.get_drafts, annotations=ToolAnnotations(title="Get Drafts", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(drafts.clear_draft, annotations=ToolAnnotations(title="Clear Draft", openWorldHint=True, destructiveHint=True))

# Stickers/GIFs Tools
mcp.add_tool(stickers.get_sticker_sets, annotations=ToolAnnotations(title="Get Sticker Sets", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(stickers.send_sticker, annotations=ToolAnnotations(title="Send Sticker", openWorldHint=True, destructiveHint=True))
mcp.add_tool(stickers.get_gif_search, annotations=ToolAnnotations(title="Get Gif Search", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(stickers.send_gif, annotations=ToolAnnotations(title="Send Gif", openWorldHint=True, destructiveHint=True))

# Bot Tools
mcp.add_tool(bots.get_bot_info, annotations=ToolAnnotations(title="Get Bot Info", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(bots.set_bot_commands, annotations=ToolAnnotations(title="Set Bot Commands", openWorldHint=True, destructiveHint=True))

# Reaction Tools
mcp.add_tool(reactions.send_reaction, annotations=ToolAnnotations(title="Send Reaction", openWorldHint=True, destructiveHint=True))
mcp.add_tool(reactions.remove_reaction, annotations=ToolAnnotations(title="Remove Reaction", openWorldHint=True, destructiveHint=True))
mcp.add_tool(reactions.get_message_reactions, annotations=ToolAnnotations(title="Get Message Reactions", openWorldHint=True, readOnlyHint=True))

# Search Tools
mcp.add_tool(search.search_public_chats, annotations=ToolAnnotations(title="Search Public Chats", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(search.resolve_username, annotations=ToolAnnotations(title="Resolve Username", openWorldHint=True, readOnlyHint=True))

# Misc Tools
mcp.add_tool(misc.get_me, annotations=ToolAnnotations(title="Get Me", openWorldHint=True, readOnlyHint=True))
mcp.add_tool(misc.get_participants, annotations=ToolAnnotations(title="Get Participants", openWorldHint=True, readOnlyHint=True))


async def _main() -> None:
    try:
        print("Starting Telegram client...")
        await client.start()
        print("Telegram client started. Running MCP server...")
        await mcp.run_stdio_async()
    except Exception as e:
        print(f"Error starting client: {e}", file=sys.stderr)
        if isinstance(e, sqlite3.OperationalError) and "database is locked" in str(e):
            print("Database lock detected.", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    nest_asyncio.apply()
    asyncio.run(_main())

if __name__ == "__main__":
    main()
