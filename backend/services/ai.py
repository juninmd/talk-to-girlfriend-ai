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
Resuma o registro de conversas a seguir em formato de "Newsletter Diária".
O log contém conversas de diferentes chats, separados por cabeçalhos.

Para cada conversa (ou grupo de conversas):
1. Identifique o tema principal.
2. Destaque decisões, ideias e o "clima" da conversa.
3. Liste tarefas ou compromissos se houver.

O resumo final deve ser uma visão geral do dia, em Português do Brasil, profissional mas leve.
Use emojis e seções claras.

Log das Conversas:
{text_log}
"""

CONVERSATION_SYSTEM_PROMPT = """
Você é um assistente pessoal inteligente, amigável e natural, que se comunica em Português do Brasil.
Seu objetivo é conversar como um humano (amigo ou colega prestativo), ser útil e lembrar de detalhes importantes.

Diretrizes:
1. **Naturalidade**: Não seja robótico. Use gírias leves se o contexto permitir, mas mantenha a educação.
2. **Memória**: Use ativamente os "Fatos Conhecidos" e o "Histórico Recente" para personalizar sua resposta. Mencione fatos lembrados quando relevante para mostrar que você se importa.
3. **Identidade**: Observe os nomes dos participantes no histórico. Use o nome do usuário para tornar a conversa mais pessoal. Se o "sender_name" for você (o bot), entenda que foi algo que você disse.
4. **Contexto**: Responda diretamente à última mensagem, mas mantenha a continuidade do assunto.
5. **Concisão**: Evite textos muito longos, a menos que solicitado ou necessário para explicar algo.

Fatos Conhecidos sobre este chat (Use estes dados para personalizar a conversa):
{facts_text}

Histórico Recente da Conversa:
{history_text}

Última mensagem: {user_message}

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

    async def summarize_conversations(self, data: Any) -> str:
        """
        Summarizes conversations.
        Accepts:
        - List[Message]: Flat list of messages (backward compatibility)
        - Dict[str, List[Message]]: Grouped by chat identifier
        """
        if not self.model or not data:
            return "Sem dados para resumir."

        text_log = ""

        if isinstance(data, list) and all(isinstance(m, Message) for m in data):
            # Flat list
            text_log = "\n".join([f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}" for m in data])
        elif isinstance(data, dict):
            # Grouped dict
            chunks = []
            for chat_name, msgs in data.items():
                chunks.append(f"--- Chat: {chat_name} ---")
                for m in msgs:
                    chunks.append(f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}")
                chunks.append("") # Empty line
            text_log = "\n".join(chunks)
        else:
            return "Formato de dados inválido para resumo."

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
            [f"[{m.date.strftime('%d/%m %H:%M')}] {m.sender_name}: {m.text}" for m in history]
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
