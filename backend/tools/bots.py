import json
from telethon import functions
from telethon.tl.types import BotCommand, BotCommandScopeDefault
from telethon.tl.functions.bots import SetBotCommandsRequest
from backend.client import client
from backend.utils import log_and_format_error, json_serializer


async def get_bot_info(bot_username: str) -> str:
    try:
        entity = await client.get_entity(bot_username)
        if not entity:
            return f"Bot {bot_username} not found."
        result = await client(functions.users.GetFullUserRequest(id=entity))
        if hasattr(result, "to_dict"):
            return json.dumps(result.to_dict(), indent=2, default=json_serializer)
        return f"Bot ID: {entity.id}, Name: {entity.first_name}"
    except Exception as e:
        return log_and_format_error("get_bot_info", e, bot_username=bot_username)


async def set_bot_commands(bot_username: str, commands: list) -> str:
    try:
        me = await client.get_me()
        if not getattr(me, "bot", False):
            return "Error: This function is for bot accounts only."
        bot_commands = [
            BotCommand(command=c["command"], description=c["description"]) for c in commands
        ]
        await client(
            SetBotCommandsRequest(
                scope=BotCommandScopeDefault(), lang_code="en", commands=bot_commands
            )
        )
        return f"Bot commands set for {bot_username}."
    except Exception as e:
        return log_and_format_error("set_bot_commands", e, bot_username=bot_username)
