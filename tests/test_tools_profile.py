import pytest
from unittest.mock import AsyncMock, patch

from backend.tools import profile


@pytest.fixture
def mock_client():
    with patch("backend.tools.profile.client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_update_profile(mock_client):
    mock_client.side_effect = AsyncMock()
    result = await profile.update_profile(first_name="Test")
    assert "Profile updated" in result


@pytest.mark.asyncio
async def test_set_profile_photo(mock_client):
    mock_client.upload_file = AsyncMock(return_value="file")
    mock_client.side_effect = AsyncMock()

    result = await profile.set_profile_photo(file_path="photo.jpg")
    assert "Profile photo updated" in result
