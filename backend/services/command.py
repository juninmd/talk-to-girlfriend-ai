import asyncio
import logging
from typing import Optional
from sqlmodel import Session, select, or_
from backend.database import engine, Fact
from backend.settings import settings
from backend.services.learning import learning_service
from backend.services.reporting import reporting_service

logger = logging.getLogger(__name__)


class CommandService:
    def __init__(self, client):
        self.client = client

    async def handle_command(
        self, chat_id: int, text: str, sender_id: Optional[int] = None
    ) -> bool:
        """
        Handles commands like /aprender, /relatorio, /fatos.
        Returns True if a command was handled, False otherwise.
        """
        text = text.strip()

        if text.startswith("/start"):
            await self._handle_start(chat_id)
            return True

        if text.startswith("/ajuda") or text.startswith("/help"):
            await self._handle_help(chat_id)
            return True

        if text.startswith("/aprender"):
            await self._handle_learn(chat_id, text)
            return True

        if text.startswith("/relatorio_global"):
            await self._handle_global_report(chat_id)
            return True

        if text.startswith("/relatorio"):
            await self._handle_report(chat_id)
            return True

        if text.startswith("/fatos"):
            await self._handle_facts(chat_id, sender_id)
            return True

        return False

    async def _handle_start(self, chat_id: int):
        welcome_message = (
            "👋 **Fala tu! Eu sou o Jules.**\n\n"
            "Sou seu Senior Software Engineer de estimação (e IA nas horas vagas).\n"
            "Tô aqui pra ajudar a organizar a bagunça, lembrar do que você esquece e garantir que a gente siga as **Boas Práticas**.\n\n"
            "**O que eu faço:**\n"
            "🧠 **Memória:** Aprendo sobre seus projetos e stack (se você deixar).\n"
            "📊 **Relatórios:** Resumo o caos do dia em algo legível.\n"
            "💡 **Contexto:** Te ajudo a não perder o fio da meada.\n\n"
            "**Comandos:**\n"
            "`/start` - Esse texto aqui.\n"
            "`/aprender [n]` - Leio as últimas n mensagens pra ficar por dentro.\n"
            "`/relatorio` - Resumo rápido dessa conversa.\n"
            "`/relatorio_global` - O resumo oficial do dia (vai pro canal).\n"
            "`/fatos` - O que eu sei sobre você (cuidado com a verdade)."
        )
        await self.client.send_message(chat_id, welcome_message)

    async def _handle_help(self, chat_id: int):
        await self._handle_start(chat_id)

    async def _handle_learn(self, chat_id: int, text: str):
        parts = text.split()
        limit = settings.LEARNING_HISTORY_LIMIT
        if len(parts) > 1:
            try:
                parsed_limit = int(parts[1])
                if parsed_limit > 0:
                    limit = min(parsed_limit, 500)  # Max limit 500
            except ValueError:
                pass

        await self.client.send_message(
            chat_id,
            f"🧠 Deixa comigo. Lendo as últimas {limit} mensagens pra pegar o contexto...",
        )

        status_msg = await learning_service.ingest_history(chat_id, limit)
        await self.client.send_message(chat_id, f"✅ {status_msg}")

    async def _handle_global_report(self, chat_id: int):
        await self.client.send_message(
            chat_id,
            "🌍 Processando relatório global... Pode demorar um pouquinho.",
        )
        report_text = await reporting_service.generate_daily_report(chat_id=None)

        if report_text:
            await self.client.send_message(chat_id, "✅ Relatório global enviado com sucesso!")
        else:
            await self.client.send_message(chat_id, "⚠️ Deu ruim. Falha ao gerar relatório.")

    async def _handle_report(self, chat_id: int):
        await self.client.send_message(
            chat_id,
            "📊 Gerando relatório local... Aguenta aí.",
        )
        report_text = await reporting_service.generate_daily_report(
            chat_id=chat_id,
        )
        if report_text:
            await self.client.send_message(chat_id, report_text)
        else:
            await self.client.send_message(
                chat_id,
                "⚠️ Não consegui gerar o relatório. Talvez não tenha mensagens novas?",
            )

    async def _handle_facts(self, chat_id: int, sender_id: Optional[int] = None):
        await self.client.send_message(chat_id, "🧠 Buscando fatos conhecidos...")

        try:
            facts = await asyncio.to_thread(self._fetch_facts, chat_id, sender_id)
            if not facts:
                await self.client.send_message(
                    chat_id, "🤷‍♂️ Não conheço nenhum fato sobre esta conversa (ou você) ainda."
                )
            else:
                response_lines = [
                    f"**Fatos Conhecidos (Últimos {settings.AI_CONTEXT_FACT_LIMIT}):**",
                    "",
                ]
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

    def _fetch_facts(self, chat_id: int, sender_id: Optional[int] = None):
        with Session(engine) as session:
            if sender_id:
                query = select(Fact).where(
                    or_(Fact.chat_id == chat_id, Fact.sender_id == sender_id)
                )
            else:
                query = select(Fact).where(Fact.chat_id == chat_id)

            statement = query.order_by(Fact.created_at.desc()).limit(
                settings.AI_CONTEXT_FACT_LIMIT
            )
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
            return session.exec(statement).all()
