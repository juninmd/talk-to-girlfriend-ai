import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
from backend.services.reporting import ReportingService
from backend.services.learning import LearningService
from backend.services.ai import AIService
from backend.database import Message


@pytest.mark.asyncio
async def test_reporting_smart_truncation():
    """
    Verifies that ReportingService prioritizes diversity (top N from each chat)
    before applying global truncation.
    """
    reporting_service = ReportingService()
    reporting_service.client = MagicMock()

    # Mock AI Service summary to avoid API call
    with patch(
        "backend.services.reporting.ai_service.summarize_conversations", new_callable=AsyncMock
    ) as mock_summary:
        mock_summary.return_value = "Summary OK"

        # Setup data: 3 Chats.
        # Chat A: 100 messages (new)
        # Chat B: 10 messages (new)
        # Chat C: 100 messages (old)

        now = datetime.now(timezone.utc)

        chat_a_msgs = [
            Message(
                id=i,
                telegram_message_id=i,
                chat_id=1,
                text=f"A{i}",
                date=now - timedelta(minutes=i),
            )
            for i in range(100)
        ]
        chat_b_msgs = [
            Message(
                id=100 + i,
                telegram_message_id=100 + i,
                chat_id=2,
                text=f"B{i}",
                date=now - timedelta(minutes=i),
            )
            for i in range(10)
        ]

        # Chat C is older
        chat_c_msgs = [
            Message(
                id=200 + i,
                telegram_message_id=200 + i,
                chat_id=3,
                text=f"C{i}",
                date=now - timedelta(hours=1, minutes=i),
            )
            for i in range(100)
        ]

        data = {"Chat A": chat_a_msgs, "Chat B": chat_b_msgs, "Chat C": chat_c_msgs}

        # We set Global Limit to 70.
        # Smart Truncation Step 1 (Per chat limit 50):
        # - Chat A: takes top 50 (A0-A49)
        # - Chat B: takes all 10 (B0-B9)
        # - Chat C: takes top 50 (C0-C49)
        # Total pool: 110 messages.

        # Smart Truncation Step 2 (Global Sort & Limit 70):
        # Sorted by date desc:
        # - B0..B9 (0-9 mins ago)
        # - A0..A49 (0-49 mins ago) -> Interleaved with B
        # - C0..C9 (60-69 mins ago)

        # Since A and B are "now", they will fill the slots first.
        # A(50) + B(10) = 60 messages.
        # We have 10 slots left for C.

        with patch("backend.services.reporting.settings.REPORT_CONTEXT_LIMIT", 70):
            await reporting_service._generate_report_content(data, 210, 3)

            # Verify call to summarize
            mock_summary.assert_called_once()
            args, _ = mock_summary.call_args
            final_data = args[0]

            # Check counts
            # We expect:
            # Chat A: 50 messages (capped)
            # Chat B: 10 messages (all)
            # Chat C: 10 messages (filling the rest of the 70 limit)

            assert len(final_data["Chat A"]) == 50
            assert len(final_data["Chat B"]) == 10
            assert len(final_data["Chat C"]) == 10


@pytest.mark.asyncio
async def test_learning_service_startup_logic():
    """
    Verifies that LearningService checks DB and triggers backfill on startup.
    """
    learning_service = LearningService()
    learning_service.client = MagicMock()
    learning_service.client.add_event_handler = MagicMock()
    learning_service.ingest_all_history = AsyncMock()

    # Mock settings
    with patch("backend.services.learning.settings.AUTO_LEARN_ON_STARTUP", True):
        # Mock _check_if_learning_needed
        with patch.object(learning_service, "_check_if_learning_needed", return_value=True):
            # Mock asyncio.sleep to avoid wait
            with patch("asyncio.sleep", new_callable=AsyncMock):
                # Call logic directly or trigger the task?
                # start_listening spawns the task.
                # We can't easily await the spawned task unless we return it.
                # So we test `_background_backfill_task` directly.

                await learning_service._background_backfill_task()

                learning_service.ingest_all_history.assert_called_once()


@pytest.mark.asyncio
async def test_ai_service_extract_facts_robustness():
    ai = AIService()
    ai.client = MagicMock()

    # Test None
    assert await ai.extract_facts(None) == []

    # Test Short
    assert await ai.extract_facts("Hi") == []
