import json
import logging
import asyncio
import re
from datetime import datetime, timezone
import google.generativeai as genai
from typing import List, Dict, Any
from sqlmodel import Session, select
from backend.database import engine, Message, Fact
from backend.config import GOOGLE_API_KEY, AI_CONTEXT_FACT_LIMIT
from backend.prompts import (
    FACT_EXTRACTION_PROMPT,
    SUMMARY_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
)
from backend.utils import async_retry

logger = logging.getLogger(__name__)

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


class AIService:
    def __init__(self):
        self.model = None
        if GOOGLE_API_KEY:
            # Using Gemini 1.5 Flash for better performance and cost-efficiency
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            logger.warning("GOOGLE_API_KEY not set. AI features disabled.")

    @async_retry(max_attempts=3, delay=1.0)
    async def extract_facts(self, text: str) -> List[Dict[str, Any]]:
        """
        Uses LLM to extract facts from text.
        Returns a list of dicts: {'entity': str, 'value': str, 'category': str}
        """
        if not self.model:
            return []

        prompt = FACT_EXTRACTION_PROMPT.format(text=text)

        try:
            # Request JSON output directly
            response = await self.model.generate_content_async(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            raw_text = response.text.strip()

            # Pre-cleaning: remove markdown code blocks
            # This helps if the model wraps output in ```json ... ``` even with mime_type set
            raw_text = raw_text.replace("```json", "").replace("```", "")

            # Use regex to find the JSON list structure [ ... ]
            # This handles any conversational preamble
            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if match:
                raw_text = match.group(0)

            facts = json.loads(raw_text)
            if isinstance(facts, list):
                return facts
            return []
        except Exception as e:
            raw_text = response.text if "response" in locals() else "N/A"
            logger.error(f"Error extracting facts: {e}. Raw text: {raw_text}")
            # Re-raise to trigger retry
            raise e

    @async_retry(max_attempts=3, delay=2.0)
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

        if isinstance(data, list) and all(
            isinstance(m, Message) for m in data
        ):
            # Flat list
            text_log = "\n".join(
                [
                    f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}"
                    for m in data
                ]
            )
        elif isinstance(data, dict):
            # Grouped dict
            chunks = []
            for chat_name, msgs in data.items():
                chunks.append(f"--- Chat: {chat_name} ---")
                for m in msgs:
                    chunks.append(
                        f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}"
                    )
                chunks.append("")  # Empty line
            text_log = "\n".join(chunks)
        else:
            return "Formato de dados inválido para resumo."

        prompt = SUMMARY_PROMPT.format(text_log=text_log)

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            raise e

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
            history = sorted(
                history, key=lambda x: x.date
            )  # sort back to chrono order

            # Get relevant facts
            facts = session.exec(
                select(Fact)
                .where(Fact.chat_id == chat_id)
                .order_by(Fact.created_at.desc())
                .limit(AI_CONTEXT_FACT_LIMIT)
            ).all()
            return history, facts

    def _format_relative_time(self, dt: datetime) -> str:
        """Helper to format datetime relatively (e.g. Today 14:00, Yesterday 10:00)."""
        now = datetime.now(timezone.utc)
        # Ensure dt is aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now.date() - dt.date()

        if diff.days == 0:
            day_str = "Hoje"
        elif diff.days == 1:
            day_str = "Ontem"
        elif diff.days < 7:
            day_str = dt.strftime("%A")  # Day name
        else:
            day_str = dt.strftime("%d/%m")

        return f"{day_str} {dt.strftime('%H:%M')}"

    @async_retry(max_attempts=2, delay=0.5)
    async def generate_natural_response(
        self, chat_id: int, user_message: str, sender_name: str = "User"
    ) -> str:
        """
        Generates a natural response using history and facts.
        """
        if not self.model:
            return "Desculpe, minha IA não está configurada."

        # 1. Retrieve Context (Non-blocking)
        try:
            history, facts = await asyncio.to_thread(
                self._get_context, chat_id
            )
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            history, facts = [], []

        history_text = "\n".join(
            [
                f"[{self._format_relative_time(m.date)}] {m.sender_name}: {m.text}"
                for m in history
            ]
        )
        facts_text = "\n".join(
            [f"- {f.entity_name} ({f.category}): {f.value}" for f in facts]
        )

        # Inject sender name into the message context
        full_user_message = f"User {sender_name} says: {user_message}"

        prompt = CONVERSATION_SYSTEM_PROMPT.format(
            facts_text=facts_text,
            history_text=history_text,
            user_message=full_user_message,
        )

        try:
            response = await self.model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise e


ai_service = AIService()
