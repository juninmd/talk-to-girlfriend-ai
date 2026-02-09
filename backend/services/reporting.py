import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

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

    @async_retry(max_attempts=3, delay=5.0)
    async def generate_daily_report(self, chat_id: int = None) -> str:
        """
        Generates a summary of all conversations from the last 24 hours.
        If chat_id is None (scheduled), it sends the report to the configured channel.
        If chat_id is provided (manual), it returns the report text.
        """
        logger.info(f"Generating daily report (Specific Chat: {chat_id})...")

        # 1. Fetch messages
        messages = await asyncio.to_thread(self._fetch_messages_for_report, chat_id)
        if not messages:
            logger.warning("No messages found for today's report.")
            return "Sem mensagens para relatar."

        # 2. Prepare data (grouping & resolving titles)
        final_data = await self._prepare_data_for_ai(messages)

        # 3. Generate Report Content
        report_text = await self._generate_report_content(
            final_data, total_msgs=len(messages), unique_chats=len(final_data)
        )

        # 4. Send Report (if scheduled)
        if not chat_id:
            await self._send_report(report_text)

        return report_text

    def _fetch_messages_for_report(self, chat_id: int = None) -> List[Message]:
        """Fetches messages in a thread."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        with Session(engine) as session:
            statement = select(Message).where(Message.date >= cutoff)
            if chat_id:
                statement = statement.where(Message.chat_id == chat_id)
            messages = session.exec(statement).all()
            return messages

    async def _prepare_data_for_ai(self, messages: List[Message]) -> Dict[str, List[Message]]:
        """Groups messages by chat and resolves chat titles."""
        grouped_msgs = {}
        for m in messages:
            if m.chat_id not in grouped_msgs:
                grouped_msgs[m.chat_id] = []
            grouped_msgs[m.chat_id].append(m)

        final_data = await self._resolve_chat_titles(grouped_msgs)
        return final_data

    async def _resolve_chat_titles(
        self, grouped_msgs: Dict[int, List[Message]]
    ) -> Dict[str, List[Message]]:
        """Resolves chat IDs to human-readable titles."""
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

    async def _generate_report_content(self, data: Any, total_msgs: int, unique_chats: int) -> str:
        """Calls AI to summarize and formats the final report."""
        stats_text = f"""
- **Total de Mensagens:** {total_msgs}
- **Conversas Ativas:** {unique_chats}
""".strip()

        summary = await ai_service.summarize_conversations(data)

        today_str = datetime.now().strftime("%d/%m/%Y")
        report_text = f"""# 📅 Relatório Diário de Conversas
**Data:** {today_str}

## 📊 Estatísticas
{stats_text}

## 📝 Resumo
{summary}"""
        return report_text

    async def _send_report(self, report_text: str):
        """Sends the report to the configured channel or fallback."""
        target_entity = await self._resolve_target_entity()

        if not target_entity:
            logger.error("No valid target entity found to send the report.")
            return

        try:
            await self.client.send_message(target_entity, report_text)
            logger.info(f"Daily report sent successfully to {target_entity.id}.")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

    async def _resolve_target_entity(self):
        """Resolves the target entity for the report (Channel or Saved Messages)."""
        target_entity = None
        if settings.REPORT_CHANNEL_ID:
            try:
                target_entity = await self.client.get_entity(settings.REPORT_CHANNEL_ID)
                logger.info(f"Resolved REPORT_CHANNEL_ID to {target_entity.id}")
            except Exception as e:
                logger.warning(
                    f"Could not resolve configured REPORT_CHANNEL_ID ({settings.REPORT_CHANNEL_ID}): {e}"
                )

        if not target_entity:
            try:
                logger.info(
                    "REPORT_CHANNEL_ID invalid or missing. Falling back to 'Saved Messages'."
                )
                target_entity = await self.client.get_me()
            except Exception as e:
                logger.error(f"Could not resolve 'me' for fallback report: {e}")
                return None

        return target_entity


reporting_service = ReportingService()
