import json
import logging
import asyncio
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

from google import genai
from google.genai import types

from sqlmodel import Session, select, or_
from backend.database import engine, Message, Fact
from backend.settings import settings
from backend.prompts import (
    FACT_EXTRACTION_PROMPT,
    SUMMARY_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
)
from backend.utils import async_retry
from backend.schemas import ExtractedFact

logger = logging.getLogger(__name__)


class AIService:
    """
    Service responsible for interacting with the Google GenAI API for:
    - Fact Extraction (Memory)
    - Conversation Summarization (Reporting)
    - Natural Language Generation (Chat)
    """

    def __init__(self):
        self.client: Optional[genai.Client] = None
        if settings.GOOGLE_API_KEY:
            self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        else:
            logger.warning("GOOGLE_API_KEY not set. AI features disabled.")

    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """
        Cleans LLM response to extract valid JSON string.
        Handles Markdown code blocks and trailing commas.
        """
        raw_text = raw_text.strip()

        # 1. Try to extract from code block first
        code_block_pattern = r"```(?:json)?\s*(.*?)```"
        match = re.search(code_block_pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            raw_text = match.group(1).strip()

        # 2. Ensure we have the list structure [ ... ]
        match_array = re.search(r"\[.*\]", raw_text, re.DOTALL)
        if match_array:
            raw_text = match_array.group(0)

        # 3. Clean up any remaining whitespace
        raw_text = raw_text.strip()

        # 4. Repair common trailing comma issue using regex
        # Replaces ", ]" with "]" and ", }" with "}"
        raw_text = re.sub(r",\s*\]", "]", raw_text)
        raw_text = re.sub(r",\s*\}", "}", raw_text)

        return raw_text

    @async_retry(max_attempts=3, delay=1.0)
    async def extract_facts(self, text: str) -> List[Dict[str, Any]]:
        """
        Uses LLM to extract facts from text.
        Returns a list of dicts conforming to ExtractedFact schema.
        """
        if not self.client:
            return []

        if not text or len(text.strip()) < 10:
            return []

        # Safe formatting
        try:
            prompt = FACT_EXTRACTION_PROMPT.format(text=text)
        except Exception as e:
            logger.error(f"Error formatting prompt for fact extraction: {e}")
            return []

        try:
            return await self._generate_and_parse_facts(prompt)
        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    async def _generate_and_parse_facts(self, prompt: str) -> List[Dict[str, Any]]:
        """Generates content from LLM and parses the JSON response."""
        response = await self.client.aio.models.generate_content(
            model=settings.AI_MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw_text = self._clean_json_response(response.text)

        try:
            facts = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}. Text: {raw_text[:100]}...")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON: {e}")
            return []

        return self._validate_facts(facts)

    def _validate_facts(self, facts: Any) -> List[Dict[str, Any]]:
        """Validates and processes extracted facts against ExtractedFact schema."""
        if not isinstance(facts, list):
            logger.warning(f"Extracted facts is not a list: {facts}")
            return []

        valid_facts = []
        for f in facts:
            try:
                if isinstance(f, dict):
                    if "category" not in f:
                        f["category"] = "general"

                    validated_fact = ExtractedFact(**f)
                    valid_facts.append(validated_fact.model_dump())
            except Exception as e:
                logger.warning(f"Validation failed for fact {f}: {e}")
                continue
        return valid_facts

    @async_retry(max_attempts=3, delay=2.0)
    async def summarize_conversations(self, data: Any) -> str:
        """
        Summarizes conversations.
        Accepts:
        - List[Message]: Flat list of messages
        - Dict[str, List[Message]]: Grouped by chat identifier
        """
        if not self.client or not data:
            return "Sem dados para resumir."

        text_log = ""

        if isinstance(data, list) and all(isinstance(m, Message) for m in data):
            text_log = "\n".join(
                [
                    f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}"
                    for m in data
                ]
            )
        elif isinstance(data, dict):
            chunks = []
            for chat_name, msgs in data.items():
                chunks.append(f"--- Chat: {chat_name} ---")
                for m in msgs:
                    chunks.append(
                        f"[{m.date.strftime('%H:%M')}] {m.sender_name or 'Desconhecido'}: {m.text}"
                    )
                chunks.append("")
            text_log = "\n".join(chunks)
        else:
            return "Formato de dados inválido para resumo."

        try:
            prompt = SUMMARY_PROMPT.format(text_log=text_log)
            response = await self.client.aio.models.generate_content(
                model=settings.AI_MODEL_NAME,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            raise e

    def _get_context(
        self, chat_id: int, sender_id: Optional[int] = None
    ) -> Tuple[List[Message], List[Fact]]:
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
            history = sorted(history, key=lambda x: x.date)

            # Retrieve facts for chat OR sender (context + personalization)
            # Implementing Tiered Retrieval for better context retention
            if sender_id:
                base_cond = or_(Fact.chat_id == chat_id, Fact.sender_id == sender_id)
            else:
                base_cond = Fact.chat_id == chat_id

            limit = settings.AI_CONTEXT_FACT_LIMIT
            collected_ids = set()
            final_facts = []

            # Tier 1: Core Identity (Personal) - High Priority
            # We want to ensure we always remember who the user is and what they like
            core_cats = ["pessoal", "relacionamento", "opiniao", "preference"]
            q1 = (
                select(Fact)
                .where(base_cond)
                .where(Fact.category.in_(core_cats))
                .order_by(Fact.created_at.desc())
                .limit(10)
            )
            facts_core = session.exec(q1).all()
            for f in facts_core:
                if f.id not in collected_ids:
                    final_facts.append(f)
                    collected_ids.add(f.id)

            # Tier 2: Work Identity (Tech/Work) - Medium Priority
            # Ensuring technical context is preserved
            work_cats = ["tech", "trabalho"]
            q2 = (
                select(Fact)
                .where(base_cond)
                .where(Fact.category.in_(work_cats))
                .order_by(Fact.created_at.desc())
                .limit(20)
            )
            facts_work = session.exec(q2).all()
            for f in facts_work:
                if f.id not in collected_ids:
                    final_facts.append(f)
                    collected_ids.add(f.id)

            # Tier 3: Recent General (Fill remaining slots)
            remaining = limit - len(final_facts)
            if remaining > 0:
                q3 = (
                    select(Fact)
                    .where(base_cond)
                    .where(Fact.id.notin_(list(collected_ids)))
                    .order_by(Fact.created_at.desc())
                    .limit(remaining)
                )
                facts_general = session.exec(q3).all()
                final_facts.extend(facts_general)

            # Sort by date descending (Newest first) so the AI sees the latest info at the top
            final_facts.sort(key=lambda x: x.created_at, reverse=True)

            return history, final_facts

    def _format_relative_time(self, dt: datetime) -> str:
        """Helper to format datetime relatively (e.g. Today 14:00, Yesterday 10:00)."""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        diff = now.date() - dt.date()

        if diff.days == 0:
            day_str = "Hoje"
        elif diff.days == 1:
            day_str = "Ontem"
        elif diff.days < 7:
            day_str = dt.strftime("%A")
        else:
            day_str = dt.strftime("%d/%m")

        return f"{day_str} {dt.strftime('%H:%M')}"

    @async_retry(max_attempts=2, delay=0.5)
    async def generate_natural_response(
        self,
        chat_id: int,
        user_message: str,
        sender_name: str = "User",
        sender_id: Optional[int] = None,
    ) -> str:
        """
        Generates a natural response using history and facts.
        Includes safety check for prompt formatting.
        """
        if not self.client:
            return "Desculpe, minha IA não está configurada."

        # 1. Retrieve Context (Non-blocking)
        try:
            history, facts = await asyncio.to_thread(self._get_context, chat_id, sender_id)
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            history, facts = [], []

        history_text = "\n".join(
            [f"[{self._format_relative_time(m.date)}] {m.sender_name}: {m.text}" for m in history]
        )
        facts_text = "\n".join([f"- {f.entity_name} ({f.category}): {f.value}" for f in facts])

        full_user_message = f"User {sender_name} says: {user_message}"

        try:
            prompt = CONVERSATION_SYSTEM_PROMPT.format(
                facts_text=facts_text, history_text=history_text, user_message=full_user_message
            )
        except Exception as e:
            logger.error(f"Error formatting conversation prompt: {e}")
            # Fallback prompt if formatting fails
            prompt = f"System: Error in context. User says: {user_message}"

        try:
            response = await self.client.aio.models.generate_content(
                model=settings.AI_MODEL_NAME,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Mano, minha API de cérebro deu timeout aqui. Tenta de novo? 😵‍💫"


ai_service = AIService()
