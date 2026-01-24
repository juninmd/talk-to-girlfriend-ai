import json
import logging
import asyncio
import re
import google.generativeai as genai
from typing import List, Dict, Any
from sqlmodel import Session, select
from backend.database import engine, Message, Fact
from backend.config import GOOGLE_API_KEY
from backend.prompts import (
    FACT_EXTRACTION_PROMPT,
    SUMMARY_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


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
            raw_text = response.text.strip()

            # Remove Markdown Code Blocks if present
            # Regex to capture content inside ```json ... ``` or just ``` ... ```
            match = re.search(r"```(?:json)?(.*?)```", raw_text, re.DOTALL)
            if match:
                clean_text = match.group(1).strip()
            else:
                clean_text = raw_text

            # Further cleanup just in case
            start_idx = clean_text.find("[")
            end_idx = clean_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                clean_text = clean_text[start_idx : end_idx + 1]

            facts = json.loads(clean_text)
            if isinstance(facts, list):
                return facts
            return []
        except Exception as e:
            logger.error(f"Error extracting facts: {e}. Raw text: {response.text if 'response' in locals() else 'N/A'}")
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
            # Get last 20 messages for better flow
            statement = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.date.desc())
                .limit(20)
            )
            history = session.exec(statement).all()
            history = sorted(history, key=lambda x: x.date)  # sort back to chrono order

            # Get relevant facts (Increased to 300 for better context window usage)
            facts = session.exec(
                select(Fact)
                .where(Fact.chat_id == chat_id)
                .order_by(Fact.created_at.desc())
                .limit(300)
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
