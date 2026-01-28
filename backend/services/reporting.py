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

    @async_retry(max_attempts=3, delay=5.0)
    async def generate_daily_report(self):
        """
        Generates a summary of all conversations from the last 24 hours
        and sends it to the configured channel.
        """
        logger.info("Generating daily report...")

        if not REPORT_CHANNEL_ID:
            logger.warning("Daily Report skipped: REPORT_CHANNEL_ID not set in environment.")
            return

        # Validate Channel ID access early
        try:
            # Check if we can access the entity. If not, we might fail sending later, so we warn early.
            # But we don't abort because get_entity might need a network call that succeeds later.
            await client.get_entity(REPORT_CHANNEL_ID)
        except Exception as e:
            logger.warning(f"Could not verify REPORT_CHANNEL_ID access early: {e}. Attempting report anyway.")

        # 1. Fetch messages from last 24h (Non-blocking)
        messages = await asyncio.to_thread(self._fetch_messages_for_report)

        if not messages:
            logger.warning("No messages found for today's report.")
            return

        # Group messages by chat_id
        grouped_msgs = {}
        for m in messages:
            if m.chat_id not in grouped_msgs:
                grouped_msgs[m.chat_id] = []
            grouped_msgs[m.chat_id].append(m)

        # Resolve titles and prepare data for AI
        final_data = {}
        for chat_id, msgs in grouped_msgs.items():
            title = f"Chat {chat_id}"
            try:
                # Try to get entity to find the name
                entity = await client.get_entity(chat_id)
                if hasattr(entity, 'title'):
                    title = entity.title
                elif hasattr(entity, 'first_name'):
                    title = f"{entity.first_name} {entity.last_name or ''}".strip()
            except Exception:
                # If we can't resolve, check if we have any sender name in the messages that matches the other person
                # This is a fallback heuristic
                pass

            # Ensure unique key by appending ID
            unique_key = f"{title} (ID: {chat_id})"
            final_data[unique_key] = msgs

        # Calculate stats
        total_msgs = len(messages)
        unique_chats = len(grouped_msgs)

        stats_text = (
            f"- **Total de Mensagens:** {total_msgs}\n"
            f"- **Conversas Ativas:** {unique_chats}"
        )

        # 2. Summarize
        summary = await ai_service.summarize_conversations(final_data)

        report_text = f"""# 📅 Relatório Diário de Conversas
**Data:** {datetime.now().strftime('%d/%m/%Y')}

## 📊 Estatísticas
{stats_text}

## 📝 Resumo
{summary}"""

        # 3. Send to Telegram Channel
        try:
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
                    logger.warning(
                        f"Could not find entity for {REPORT_CHANNEL_ID}. Ensure bot is admin or joined."
                    )
            except Exception as entity_err:
                logger.error(f"Could not resolve channel {REPORT_CHANNEL_ID}: {entity_err}")
                raise entity_err
        except Exception as e:
            logger.error(f"Failed to send daily report: {e}")
            raise e


reporting_service = ReportingService()
