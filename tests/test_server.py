import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# We need to mock FastMCP before importing server
with patch("mcp.server.fastmcp.FastMCP"):
    from backend import server

@pytest.fixture
def mock_mcp():
    with patch("backend.server.mcp") as mock:
        yield mock

@pytest.fixture
def mock_client():
    with patch("backend.server.client") as mock:
        yield mock

@pytest.fixture
def mock_learning_service():
    with patch("backend.server.learning_service") as mock:
        yield mock

@pytest.fixture
def mock_reporting_service():
    with patch("backend.server.reporting_service") as mock:
        yield mock

@pytest.fixture
def mock_scheduler():
    with patch("backend.server.AsyncIOScheduler") as mock:
        yield mock

@pytest.mark.asyncio
async def test_main_function(mock_client, mock_learning_service, mock_reporting_service, mock_scheduler, mock_mcp):
    with patch("backend.server.create_db_and_tables") as mock_db:
        # Mocking _main execution by running it manually or mocking asyncio.run
        # Since main() calls asyncio.run(_main()), we can just call _main directly if we can access it.
        # It is exposed as server._main

        # Prevent infinite loop or blocking calls
        mock_mcp.run_stdio_async = AsyncMock()
        mock_client.start = AsyncMock()
        mock_learning_service.start_listening = AsyncMock()

        await server._main()

        mock_db.assert_called_once()
        mock_client.start.assert_called_once()
        mock_learning_service.start_listening.assert_called_once()
        mock_mcp.run_stdio_async.assert_called_once()
        mock_scheduler.return_value.start.assert_called_once()
        mock_scheduler.return_value.add_job.assert_called()

@pytest.mark.asyncio
async def test_main_entry_point():
    # Test main() wrapper
    with patch("asyncio.run") as mock_run:
        with patch("nest_asyncio.apply") as mock_nest:
            server.main()
            mock_nest.assert_called_once()
            mock_run.assert_called_once()

            # Close the coroutine to avoid RuntimeWarning
            args, _ = mock_run.call_args
            if args and asyncio.iscoroutine(args[0]):
                args[0].close()

@pytest.mark.asyncio
async def test_main_exception(mock_client):
    # Test exception handling in _main
    mock_client.start = AsyncMock(side_effect=Exception("Connection failed"))

    with patch("backend.server.logger") as mock_logger:
        with pytest.raises(SystemExit):
            await server._main()

        mock_logger.error.assert_called()
