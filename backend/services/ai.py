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
Analyze the following text and extract any specific facts, preferences, dates, or names mentioned.
Ignore general chitchat or greeting unless it contains specific info (e.g., "Hi, I'm Bob").
Return ONLY a JSON array of objects with keys: "entity", "value", "category".

Text: "{text}"

Example JSON:
[
    {{"entity": "User Name", "value": "John", "category": "personal"}},
    {{"entity": "Appointment", "value": "Tuesday at 5pm", "category": "schedule"}}
]
"""

SUMMARY_PROMPT = """
Summarize the following conversation log. Highlight key topics, decisions, and mood.
Write the summary in Portuguese.

Log:
{text_log}
"""

CONVERSATION_SYSTEM_PROMPT = """
Você é um assistente pessoal inteligente, amigável e natural.
Seu objetivo é conversar como um humano, ser útil e lembrar de detalhes importantes.
Não seja excessivamente formal, mas mantenha o respeito.
Use o contexto das conversas anteriores e fatos que você sabe para personalizar a resposta.
Se não souber algo, admita ou pergunte.

Fatos Conhecidos sobre este chat:
{facts_text}

Histórico Recente:
{history_text}

Última mensagem do Usuário: {user_message}

Resposta (em Português):
"""

class AIService:
    def __init__(self):
        self.model = None
        if GOOGLE_API_KEY:
            self.model = genai.GenerativeModel('gemini-pro')
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
            start_idx = clean_text.find('[')
            end_idx = clean_text.rfind(']')
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx:end_idx+1]

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
            return "No messages to summarize."

        text_log = "\n".join([f"{m.sender_name or 'Unknown'}: {m.text}" for m in messages])

        prompt = SUMMARY_PROMPT.format(text_log=text_log)

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            return "Error generating summary."

    def _get_context(self, chat_id: int):
        """Helper to fetch DB context synchronously."""
        with Session(engine) as session:
            # Get last 15 messages for flow
            statement = select(Message).where(Message.chat_id == chat_id).order_by(Message.date.desc()).limit(15)
            history = session.exec(statement).all()
            history = sorted(history, key=lambda x: x.date) # sort back to chrono order

            # Get relevant facts
            facts = session.exec(select(Fact).where(Fact.chat_id == chat_id).order_by(Fact.created_at.desc()).limit(30)).all()
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

        history_text = "\n".join([f"{'Bot' if m.is_outgoing else 'User'}: {m.text}" for m in history])
        facts_text = "\n".join([f"- {f.entity_name}: {f.value}" for f in facts])

        prompt = CONVERSATION_SYSTEM_PROMPT.format(
            facts_text=facts_text,
            history_text=history_text,
            user_message=user_message
        )

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Desculpe, não consegui processar isso agora."

ai_service = AIService()
