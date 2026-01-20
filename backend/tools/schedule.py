from typing import Union
from datetime import datetime, timedelta
from backend.client import client
from backend.utils import log_and_format_error, validate_id


@validate_id("chat_id")
async def schedule_message(chat_id: Union[int, str], message: str, minutes_from_now: int) -> str:
    try:
        if minutes_from_now < 1:
            return "Error: minutes_from_now must be at least 1"
        if minutes_from_now > 525600:
            return "Error: minutes_from_now cannot exceed 525600 (1 year)"

        entity = await client.get_entity(chat_id)
        schedule_time = datetime.now() + timedelta(minutes=minutes_from_now)
        await client.send_message(entity, message, schedule=schedule_time)
        return f"Message scheduled for {schedule_time.strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        return log_and_format_error("schedule_message", e, chat_id=chat_id)
