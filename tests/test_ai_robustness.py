import pytest
from unittest.mock import MagicMock, AsyncMock
import os

# Set dummy env vars
os.environ["TELEGRAM_API_ID"] = "123"
os.environ["TELEGRAM_API_HASH"] = "abc"
os.environ["GOOGLE_API_KEY"] = "xyz"

from backend.services.ai import AIService

@pytest.mark.asyncio
async def test_extract_facts_with_markdown_blocks():
    service = AIService()
    service.model = MagicMock()

    # Mock response with Markdown code blocks
    markdown_response = """
    Here is the JSON you requested:
    ```json
    [
        {"entity": "Project", "value": "Apollo", "category": "work"},
        {"entity": "Hobby", "value": "Guitar", "category": "personal"}
    ]
    ```
    Hope this helps!
    """

    service.model.generate_content_async = AsyncMock(
        return_value=MagicMock(text=markdown_response)
    )

    facts = await service.extract_facts("Text doesn't matter here due to mock")

    assert len(facts) == 2
    assert facts[0]["value"] == "Apollo"
    assert facts[1]["value"] == "Guitar"

@pytest.mark.asyncio
async def test_extract_facts_with_generic_markdown_blocks():
    service = AIService()
    service.model = MagicMock()

    # Mock response with generic code blocks
    markdown_response = """
    ```
    [
        {"entity": "City", "value": "Rio", "category": "location"}
    ]
    ```
    """

    service.model.generate_content_async = AsyncMock(
        return_value=MagicMock(text=markdown_response)
    )

    facts = await service.extract_facts("Text doesn't matter")

    assert len(facts) == 1
    assert facts[0]["value"] == "Rio"
