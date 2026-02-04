import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from backend.database import engine, Message
from backend.services.ai import ai_service
from backend.client import client
from backend.settings import settings
from backend.utils import async_retry, format_entity

logger = logging.getLogger(__name__)


class ReportingService:
    def __init__(self):
        self.client = client

    def _fetch_messages_for_report(self, chat_id: int = None):
        """Fetches messages in a thread."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        with Session(engine) as session:
            statement = select(Message).where(Message.date >= cutoff)
            if chat_id:
                statement = statement.where(Message.chat_id == chat_id)
            messages = session.exec(statement).all()
            return messages

    @async_retry(max_attempts=3, delay=5.0)
    async def generate_daily_report(self, chat_id: int = None) -> str:
        """
        Generates a summary of all conversations from the last 24 hours
        and sends it to the configured channel.
        Returns the report text.
        """
        logger.info(
            f"Generating daily report (Specific Chat: {chat_id})...",
        )

        target_entity = None
        # If chat_id is specified (e.g. via command), we might want to send it there?
        # For now, let's keep the logic:
        # 1. If triggered by scheduler (chat_id=None) -> Send to REPORT_CHANNEL_ID
        # 2. If triggered by command (chat_id=123) -> Return text, maybe send to 123?

        # Let's resolve the target first just in case we need to send it.
        if settings.REPORT_CHANNEL_ID:
            try:
                target_entity = await self.client.get_entity(
                    settings.REPORT_CHANNEL_ID,
                )
                logger.info(f"Resolved REPORT_CHANNEL_ID to {target_entity.id}")
            except Exception as e:
                logger.warning(
                    f"Could not resolve configured REPORT_CHANNEL_ID "
                    f"({settings.REPORT_CHANNEL_ID}): {e}"
                )

        # Fallback to 'me' (Saved Messages) if no channel is set or if resolution failed
        if not target_entity:
            try:
                logger.info(
                    "REPORT_CHANNEL_ID invalid or missing. " "Falling back to 'Saved Messages'."
                )
                target_entity = await self.client.get_me()
            except Exception as e:
                logger.error(f"Could not resolve 'me' for fallback report: {e}")
                return

        # 1. Fetch messages from last 24h (Non-blocking)
        messages = await asyncio.to_thread(
            self._fetch_messages_for_report,
            chat_id,
        )

        if not messages:
            logger.warning("No messages found for today's report.")
            return "Sem mensagens para relatar."

        # Group messages by chat_id
        grouped_msgs = {}
        for m in messages:
            if m.chat_id not in grouped_msgs:
                grouped_msgs[m.chat_id] = []
            grouped_msgs[m.chat_id].append(m)

        # Resolve titles and prepare data for AI
        final_data = await self._resolve_chat_titles(grouped_msgs)

        # Calculate stats
        total_msgs = len(messages)
        unique_chats = len(grouped_msgs)

        stats_text = (
            f"- **Total de Mensagens:** {total_msgs}\n" + f"- **Conversas Ativas:** {unique_chats}"
        )

        # 2. Summarize
        summary = await ai_service.summarize_conversations(final_data)

        today_str = datetime.now().strftime("%d/%m/%Y")
        report_text = f"""# 📅 Relatório Diário de Conversas
**Data:** {today_str}

## 📊 Estatísticas
{stats_text}

## 📝 Resumo
{summary}"""

        # 3. Send to Telegram Channel (or Fallback) - ONLY if it's the global report
        # If chat_id is specified, we assume the caller handles the sending or we send it to that chat.
        # But to avoid confusion, if chat_id is provided, let's return the text and ALSO send it to the user who requested it.

        # Logic:
        # - If scheduled (no chat_id): Send to REPORT_CHANNEL_ID.
        # - If manual (chat_id): Return text. (Caller sends it).

        if not chat_id:
            try:
                if target_entity:
                    await self.client.send_message(target_entity, report_text)
                    logger.info(
                        f"Daily report sent successfully to {target_entity.id}.",
                    )
                else:
                    logger.error("No valid target entity found to send the report.")
            except Exception as e:
                logger.error(f"Failed to send daily report: {e}")
                # We don't raise here to avoid crashing the scheduler

        return report_text

    async def _resolve_chat_titles(self, grouped_msgs):
        final_data = {}
        for chat_id, msgs in grouped_msgs.items():
            title = f"Chat {chat_id}"
            try:
                entity = await self.client.get_entity(chat_id)
                formatted = format_entity(entity)
                title = formatted.get("name", title)
            except Exception:
                pass

            unique_key = f"{title} (ID: {chat_id})"
            final_data[unique_key] = msgs
        return final_data


reporting_service = ReportingService()
