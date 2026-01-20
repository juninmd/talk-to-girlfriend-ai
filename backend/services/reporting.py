import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from backend.database import engine, Message
from backend.services.ai import ai_service
from backend.client import client
from backend.config import REPORT_CHANNEL_ID

logger = logging.getLogger(__name__)

class ReportingService:
    async def _fetch_messages_for_report(self):
        """Fetches messages in a thread."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        with Session(engine) as session:
            statement = select(Message).where(Message.date >= cutoff)
            messages = session.exec(statement).all()
            return messages

    async def generate_daily_report(self):
        """
        Generates a summary of all conversations from the last 24 hours
        and sends it to the configured channel.
        """
        logger.info("Generating daily report...")

        # 1. Fetch messages from last 24h (Non-blocking)
        messages = await asyncio.to_thread(self._fetch_messages_for_report)

        if not messages:
            logger.info("No messages found for today's report.")
            return

        # Calculate stats
        total_msgs = len(messages)
        unique_chats = len(set(m.chat_id for m in messages))
        stats_text = f"📊 **Estatísticas:** {total_msgs} mensagens processadas em {unique_chats} conversas ativas."

        # 2. Summarize
        summary = await ai_service.summarize_conversations(messages)
        report_text = f"**Relatório Diário de Conversas** 📅 {datetime.now().strftime('%d/%m/%Y')}\n\n{stats_text}\n\n{summary}"

        # 3. Send to Telegram Channel
        try:
            if REPORT_CHANNEL_ID:
                try:
                    # Try sending directly if ID is valid
                    # For channels/supergroups, we usually need the entity cached or access hash
                    # If we can't find it, we try to get it first
                    try:
                        entity = await client.get_entity(REPORT_CHANNEL_ID)
                        await client.send_message(entity, report_text)
                        logger.info(f"Daily report sent successfully to {REPORT_CHANNEL_ID}.")
                    except ValueError:
                        # Sometimes get_entity fails if not seen before
                        logger.warning(f"Could not find entity for {REPORT_CHANNEL_ID}. Ensure bot is admin or joined.")
                except Exception as entity_err:
                    logger.error(f"Could not resolve channel {REPORT_CHANNEL_ID}: {entity_err}")
            else:
                logger.warning(f"REPORT_CHANNEL_ID not set. Report generated but not sent:\n{report_text}")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

reporting_service = ReportingService()
