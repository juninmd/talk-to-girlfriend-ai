import asyncio
import logging
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.database import engine, Message
from backend.services.ai import ai_service
from backend.client import client

logger = logging.getLogger(__name__)

class ReportingService:
    async def _fetch_messages_for_report(self):
        """Fetches messages in a thread."""
        cutoff = datetime.utcnow() - timedelta(days=1)
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

        # 2. Summarize
        summary = await ai_service.summarize_conversations(messages)
        report_text = f"**Relatório Diário de Conversas** 📅 {datetime.now().strftime('%d/%m/%Y')}\n\n{summary}"

        # 3. Send to Telegram Channel
        try:
            import os
            # Default to None, user must configure
            channel_id_str = os.getenv("REPORT_CHANNEL_ID")

            if channel_id_str:
                try:
                    channel_id = int(channel_id_str)
                    # Using client directly to avoid ImportErrors with wrapper services
                    # Note: We need to resolve the entity first usually, or pass ID if it's a known peer
                    # For channels, -100... ID should work directly if cached, otherwise get_entity needed.
                    try:
                        entity = await client.get_entity(channel_id)
                        await client.send_message(entity, report_text)
                        logger.info(f"Daily report sent successfully to {channel_id}.")
                    except Exception as entity_err:
                        logger.error(f"Could not resolve channel {channel_id}: {entity_err}")
                except ValueError:
                    logger.error("REPORT_CHANNEL_ID is not a valid integer.")
            else:
                logger.warning(f"REPORT_CHANNEL_ID not set. Report generated but not sent:\n{report_text}")
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")

reporting_service = ReportingService()
