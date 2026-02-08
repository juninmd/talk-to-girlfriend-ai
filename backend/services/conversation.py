import asyncio
import logging
import random
from telethon.tl.types import User
from sqlmodel import Session, select
from backend.database import engine, Fact
from backend.client import client
from backend.services.ai import ai_service
from backend.services.learning import learning_service
from backend.services.reporting import reporting_service
from backend.settings import settings
from backend.utils import get_sender_name

logger = logging.getLogger(__name__)


class ConversationService:
    def __init__(self):
        self.client = client

    async def handle_incoming_message(self, event):
        """
        Handles incoming messages and decides whether to reply.
        """
        try:
            # Basic checks: Not outgoing, Has text
            if event.message.out or not event.message.message:
                return

            # Check if sender is a bot
            if event.sender and isinstance(event.sender, User) and event.sender.bot:
                return

            # Reply if private chat OR explicitly mentioned in a group
            is_mentioned = getattr(event.message, "mentioned", False)
            should_reply = event.is_private or is_mentioned

            if not should_reply:
                return

            text = event.message.message
            chat_id = event.chat_id
            reply_to_msg_id = event.message.id if not event.is_private else None

            # --- Command Handling ---
            if await self._handle_commands(chat_id, text):
                return
            # ------------------------

            # Determine sender name
            sender_name = get_sender_name(event.message) or "Unknown"

            # Trigger reply
            asyncio.create_task(
                self._generate_and_send_reply(
                    chat_id, text, sender_name, reply_to_msg_id=reply_to_msg_id
                )
            )

        except Exception as e:
            logger.error(f"Error in ConversationService handler: {e}")

    async def _generate_and_send_reply(
        self,
        chat_id: int,
        user_message: str,
        sender_name: str,
        reply_to_msg_id: int = None,
    ):
        """Generates a response using AI and sends it."""
        try:
            # Simulate processing/reading time with jitter
            base_delay = max(
                settings.CONVERSATION_MIN_DELAY,
                len(user_message) * settings.CONVERSATION_TYPING_SPEED,
            )
            # Add random jitter (±20%)
            jitter = random.uniform(0.8, 1.2)
            delay = min(settings.CONVERSATION_MAX_DELAY, base_delay * jitter)

            await asyncio.sleep(delay)

            async with self.client.action(chat_id, "typing"):
                # Generate response
                response_text = await ai_service.generate_natural_response(
                    chat_id, user_message, sender_name
                )

                # Wait a bit more to simulate typing the response
                base_typing_delay = len(response_text) * settings.CONVERSATION_TYPING_SPEED
                typing_delay = min(
                    settings.CONVERSATION_MAX_DELAY * 1.5,
                    base_typing_delay * random.uniform(0.8, 1.2)
                )
                await asyncio.sleep(typing_delay)

                if response_text:
                    await self.client.send_message(
                        chat_id, response_text, reply_to=reply_to_msg_id
                    )
                    logger.info(f"Sent reply to chat {chat_id} (User: {sender_name})")
        except Exception as e:
            logger.error(f"Error sending reply to {chat_id}: {e}")

    async def _handle_commands(self, chat_id: int, text: str) -> bool:
        """
        Handles commands like /aprender, /relatorio, /fatos.
        Returns True if a command was handled, False otherwise.
        """
        text = text.strip()

        if text.startswith("/aprender"):
            parts = text.split()
            limit = 50
            if len(parts) > 1:
                try:
                    parsed_limit = int(parts[1])
                    if parsed_limit > 0:
                        limit = parsed_limit
                except ValueError:
                    pass

            # Feedback to user
            await self.client.send_message(
                chat_id,
                f"🧠 Iniciando aprendizado das últimas {limit} mensagens...",
            )

            status_msg = await learning_service.ingest_history(chat_id, limit)
            await self.client.send_message(chat_id, f"✅ {status_msg}")
            return True

        if text.startswith("/relatorio_global"):
            await self.client.send_message(
                chat_id,
                "🌍 Gerando e enviando relatório global...",
            )
            # chat_id=None triggers sending to the configured channel
            report_text = await reporting_service.generate_daily_report(chat_id=None)

            if report_text:
                await self.client.send_message(chat_id, "✅ Relatório global enviado!")
            else:
                await self.client.send_message(chat_id, "⚠️ Falha ao gerar relatório.")
            return True

        if text.startswith("/relatorio"):
            await self.client.send_message(
                chat_id,
                "📊 Gerando relatório para esta conversa...",
            )
            report_text = await reporting_service.generate_daily_report(
                chat_id=chat_id,
            )
            if report_text:
                await self.client.send_message(chat_id, report_text)
            else:
                await self.client.send_message(
                    chat_id,
                    "⚠️ Não foi possível gerar o relatório.",
                )
            return True

        if text.startswith("/fatos"):
            await self.client.send_message(chat_id, "🧠 Buscando fatos conhecidos...")

            try:
                facts = await asyncio.to_thread(self._fetch_facts, chat_id)
                if not facts:
                    await self.client.send_message(
                        chat_id, "🤷‍♂️ Não conheço nenhum fato sobre esta conversa ainda."
                    )
                else:
                    response_lines = ["**Fatos Conhecidos:**", ""]
                    grouped = {}
                    for f in facts:
                        if f.category not in grouped:
                            grouped[f.category] = []
                        grouped[f.category].append(f"{f.entity_name}: {f.value}")

                    for category, items in grouped.items():
                        response_lines.append(f"_{category.capitalize()}_")
                        for item in items:
                            response_lines.append(f"• {item}")
                        response_lines.append("")

                    await self.client.send_message(chat_id, "\n".join(response_lines))
            except Exception as e:
                logger.error(f"Error fetching facts: {e}")
                await self.client.send_message(chat_id, "❌ Erro ao buscar fatos.")
            return True

        return False

    def _fetch_facts(self, chat_id: int):
        with Session(engine) as session:
            statement = select(Fact).where(Fact.chat_id == chat_id)
            return session.exec(statement).all()


conversation_service = ConversationService()
