import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from backend.database import engine, Message
from backend.services.ai import ai_service
from backend.client import client
from backend.config import REPORT_CHANNEL_ID
from backend.utils import async_retry

logger = logging.getLogger(__name__)


class ReportingService:
    def _fetch_messages_for_report(self):
        """Fetches messages in a thread."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        with Session(engine) as session:
            statement = select(Message).where(Message.date >= cutoff)
            messages = session.exec(statement).all()
            return messages

    async def _resolve_chat_titles(self, grouped_msgs):
        """Resolves chat titles for grouped messages."""
        final_data = {}
        for chat_id, msgs in grouped_msgs.items():
            title = f"Chat {chat_id}"
            try:
                entity = await client.get_entity(chat_id)
                if hasattr(entity, "title"):
                    title = entity.title
                elif hasattr(entity, "first_name"):
                    title = (
                        f"{entity.first_name} {entity.last_name or ''}".strip()
                    )
            except Exception:
                pass
            unique_key = f"{title} (ID: {chat_id})"
            final_data[unique_key] = msgs
        return final_data

    @async_retry(max_attempts=3, delay=5.0)
    async def generate_daily_report(self):
        """
        Generates a summary of all conversations from the last 24 hours
        and sends it to the configured channel.
        """
        logger.info("Generating daily report...")

        if not REPORT_CHANNEL_ID:
            logger.warning(
                "Daily Report skipped: REPORT_CHANNEL_ID not set in environment."
            )
            return

        try:
            await client.get_entity(REPORT_CHANNEL_ID)
        except Exception as e:
            logger.warning(
                f"Could not verify REPORT_CHANNEL_ID access early: {e}. Attempting report anyway."
            )

        messages = await asyncio.to_thread(self._fetch_messages_for_report)
        if not messages:
            logger.warning("No messages found for today's report.")
            return

        grouped_msgs = {}
        for m in messages:
            if m.chat_id not in grouped_msgs:
                grouped_msgs[m.chat_id] = []
            grouped_msgs[m.chat_id].append(m)

        final_data = await self._resolve_chat_titles(grouped_msgs)

        total_msgs = len(messages)
        unique_chats = len(grouped_msgs)
        stats_text = (
            f"- **Total de Mensagens:** {total_msgs}\n"
            f"- **Conversas Ativas:** {unique_chats}"
        )

        summary = await ai_service.summarize_conversations(final_data)

        report_text = f"""# 📅 Relatório Diário de Conversas
**Data:** {datetime.now().strftime('%d/%m/%Y')}

## 📊 Estatísticas
{stats_text}

## 📝 Resumo
{summary}"""

        try:
            try:
                entity = await client.get_entity(REPORT_CHANNEL_ID)
                await client.send_message(entity, report_text)
                logger.info(
                    f"Daily report sent successfully to {REPORT_CHANNEL_ID}."
                )
            except ValueError:
                logger.warning(
                    f"Could not find entity for {REPORT_CHANNEL_ID}. Ensure bot is admin or joined."
                )
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            raise e


reporting_service = ReportingService()
