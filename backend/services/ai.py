import json
import logging
import asyncio
import google.generativeai as genai
from typing import List, Dict, Any
from sqlmodel import Session, select
from backend.database import engine, Message, Fact
from backend.config import GOOGLE_API_KEY

logger = logging.getLogger(__name__)

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Prompts
FACT_EXTRACTION_PROMPT = """
Analise o texto a seguir e extraia fatos específicos, preferências, datas importantes, nomes de pessoas, hobbies ou informações profissionais mencionadas.
Ignore conversas fiadas (chitchat) ou saudações, a menos que contenham informações específicas (ex: "Oi, sou o Bruno").
O objetivo é construir uma memória de longo prazo sobre o usuário e o contexto.

Texto: "{text}"

Retorne APENAS um array JSON de objetos com as chaves: "entity" (entidade), "value" (valor), "category" (categoria).
Categorias sugeridas: "pessoal", "trabalho", "preferência", "agenda", "relacionamento", "localização".

Exemplo JSON:
[
    {{"entity": "Nome do Usuário", "value": "João Silva", "category": "pessoal"}},
    {{"entity": "Time de Futebol", "value": "Flamengo", "category": "preferência"}},
    {{"entity": "Reunião", "value": "Terça às 17h com a equipe de TI", "category": "agenda"}}
]
"""

SUMMARY_PROMPT = """
Resuma o registro de conversa a seguir em formato de "Newsletter Diária".
Destaque os tópicos principais, decisões tomadas, ideias discutidas e o "clima" geral das conversas.
Se houver tarefas ou compromissos mencionados, liste-os separadamente.

O resumo deve ser em Português do Brasil, com tom profissional mas leve.
Use emojis para organizar.

Log:
{text_log}
"""

CONVERSATION_SYSTEM_PROMPT = """
Você é um assistente pessoal inteligente, amigável e natural, que se comunica em Português do Brasil.
Seu objetivo é conversar como um humano (amigo ou colega prestativo), ser útil e lembrar de detalhes importantes.

Diretrizes:
1. **Naturalidade**: Não seja robótico. Use gírias leves se o contexto permitir, mas mantenha a educação.
2. **Memória**: Use ativamente os "Fatos Conhecidos" e o "Histórico Recente" para personalizar sua resposta. Se o usuário já disse que gosta de X, não pergunte novamente, apenas mencione.
3. **Contexto**: Responda diretamente à última mensagem, mas considerando o fluxo da conversa.
4. **Honestidade**: Se não souber algo, admita ou pergunte para aprender.
5. **Concisão**: Evite textos muito longos, a menos que seja solicitado uma explicação detalhada.

Fatos Conhecidos sobre este chat:
{facts_text}

Histórico Recente da Conversa:
{history_text}

Última mensagem do Usuário: {user_message}

Sua Resposta (em Português):
"""


class AIService:
    def __init__(self):
        self.model = None
        if GOOGLE_API_KEY:
            self.model = genai.GenerativeModel("gemini-pro")
        else:
            logger.warning("GOOGLE_API_KEY not set. AI features disabled.")

    async def extract_facts(self, text: str) -> List[Dict[str, Any]]:
        """
        Uses LLM to extract facts from text.
        Returns a list of dicts: {'entity': str, 'value': str, 'category': str}
        """
        if not self.model:
            return []

        prompt = FACT_EXTRACTION_PROMPT.format(text=text)

        try:
            response = await self.model.generate_content_async(prompt)
            # Basic cleanup to ensure JSON parsing
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            # Handle case where LLM might add extra text
            start_idx = clean_text.find("[")
            end_idx = clean_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx : end_idx + 1]

            facts = json.loads(clean_text)
            if isinstance(facts, list):
                return facts
            return []
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    async def summarize_conversations(self, messages: List[Message]) -> str:
        """Summarizes a list of message objects."""
        if not self.model or not messages:
            return "Sem mensagens para resumir."

        text_log = "\n".join([f"{m.sender_name or 'Desconhecido'}: {m.text}" for m in messages])

        prompt = SUMMARY_PROMPT.format(text_log=text_log)

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            return "Erro ao gerar resumo."

    def _get_context(self, chat_id: int):
        """Helper to fetch DB context synchronously."""
        with Session(engine) as session:
            # Get last 20 messages for better flow (increased from 15)
            statement = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.date.desc())
                .limit(20)
            )
            history = session.exec(statement).all()
            history = sorted(history, key=lambda x: x.date)  # sort back to chrono order

            # Get relevant facts
            facts = session.exec(
                select(Fact)
                .where(Fact.chat_id == chat_id)
                .order_by(Fact.created_at.desc())
                .limit(30)
            ).all()
            return history, facts

    async def generate_natural_response(self, chat_id: int, user_message: str) -> str:
        """
        Generates a natural response using history and facts.
        """
        if not self.model:
            return "Desculpe, minha IA não está configurada."

        # 1. Retrieve Context (Non-blocking)
        try:
            history, facts = await asyncio.to_thread(self._get_context, chat_id)
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            history, facts = [], []

        history_text = "\n".join(
            [f"{'Bot' if m.is_outgoing else 'User'}: {m.text}" for m in history]
        )
        facts_text = "\n".join([f"- {f.entity_name} ({f.category}): {f.value}" for f in facts])

        prompt = CONVERSATION_SYSTEM_PROMPT.format(
            facts_text=facts_text, history_text=history_text, user_message=user_message
        )

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Desculpe, não consegui processar isso agora."


ai_service = AIService()
