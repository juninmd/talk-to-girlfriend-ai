import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from backend.services.reporting import ReportingService
from backend.database import Message


@pytest.mark.asyncio
async def test_reporting_grouping_logic():
    # Setup
    reporting_service = ReportingService()

    # Mock messages from different chats
    msg1 = Message(
        telegram_message_id=1,
        chat_id=100,
        sender_id=1,
        sender_name="Alice",
        text="Hello",
        date=datetime.now(timezone.utc),
        is_outgoing=False,
    )
    msg2 = Message(
        telegram_message_id=2,
        chat_id=100,
        sender_id=2,
        sender_name="Bob",
        text="Hi Alice",
        date=datetime.now(timezone.utc),
        is_outgoing=False,
    )
    msg3 = Message(
        telegram_message_id=3,
        chat_id=200,
        sender_id=3,
        sender_name="Charlie",
        text="Work update",
        date=datetime.now(timezone.utc),
        is_outgoing=False,
    )

    # Mock dependencies
    with patch.object(
        reporting_service,
        "_fetch_messages_for_report",
        return_value=[msg1, msg2, msg3],
    ):
        with patch(
            "backend.services.reporting.ai_service.summarize_conversations",
            new_callable=AsyncMock,
        ) as mock_summarize:
            with patch("backend.services.reporting.client") as mock_client:
                # Mock client.get_entity to return objects with title/first_name
                mock_entity_100 = MagicMock()
                mock_entity_100.title = "Project Alpha"

                mock_entity_200 = MagicMock()
                mock_entity_200.first_name = "Charlie"
                mock_entity_200.last_name = "Smith"
                del mock_entity_200.title  # Ensure it falls back to name

                async def get_entity_side_effect(chat_id):
                    if chat_id == 100:
                        return mock_entity_100
                    if chat_id == 200:
                        return mock_entity_200
                    if chat_id == 999:
                        return MagicMock()  # REPORT_CHANNEL_ID
                    raise ValueError("Not found")

                mock_client.get_entity.side_effect = get_entity_side_effect
                mock_client.send_message = AsyncMock()

                # Patch REPORT_CHANNEL_ID to ensure execution proceeds
                with patch(
                    "backend.services.reporting.REPORT_CHANNEL_ID", 999
                ):
                    mock_summarize.return_value = "Summary generated."

                    # Act
                    await reporting_service.generate_daily_report()

                    # Assert
                    assert mock_summarize.called
                    args, _ = mock_summarize.call_args
                    data = args[0]

                    # Check keys (Chat Titles)
                    assert "Project Alpha (ID: 100)" in data
                    assert "Charlie Smith (ID: 200)" in data

                    # Check content grouping
                    assert len(data["Project Alpha (ID: 100)"]) == 2
                    assert len(data["Charlie Smith (ID: 200)"]) == 1
