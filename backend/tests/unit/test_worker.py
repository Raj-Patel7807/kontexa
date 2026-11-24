"""Unit tests for the Kontexa background worker service."""

from unittest.mock import AsyncMock, patch

import pytest

from kontexa.worker.main import WorkerService


@pytest.mark.asyncio
async def test_worker_initialization() -> None:
    """Verify worker initializes in an idle, non-running state."""
    worker = WorkerService()
    assert worker.is_running is False
    assert not worker._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_worker_start_and_stop_lifecycle() -> None:
    """Verify worker verifies dependencies on startup and closes connections on stop."""
    worker = WorkerService()

    with (
        patch("kontexa.worker.main.check_database_connection", new_callable=AsyncMock) as mock_db,
        patch("kontexa.worker.main.check_redis_connection", new_callable=AsyncMock) as mock_redis,
        patch("kontexa.worker.main.close_database_engine", new_callable=AsyncMock) as (
            mock_close_db
        ),
        patch("kontexa.worker.main.close_redis_connection", new_callable=AsyncMock) as (
            mock_close_redis
        ),
    ):
        await worker.start()
        assert worker.is_running is True
        mock_db.assert_awaited_once()
        mock_redis.assert_awaited_once()

        await worker.stop()
        assert worker.is_running is False
        assert worker._shutdown_event.is_set()
        mock_close_redis.assert_awaited_once()
        mock_close_db.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_run_with_max_iterations() -> None:
    """Verify worker polling loop runs for specified iterations and stops cleanly."""
    worker = WorkerService()

    with (
        patch("kontexa.worker.main.check_database_connection", new_callable=AsyncMock),
        patch("kontexa.worker.main.check_redis_connection", new_callable=AsyncMock),
        patch("kontexa.worker.main.close_database_engine", new_callable=AsyncMock),
        patch("kontexa.worker.main.close_redis_connection", new_callable=AsyncMock),
    ):
        await worker.run(max_iterations=1)
        assert worker.is_running is False


@pytest.mark.asyncio
async def test_worker_graceful_handling_of_dependency_failure_on_start() -> None:
    """Verify worker startup warns on dependency failure without crashing."""
    worker = WorkerService()

    with (
        patch(
            "kontexa.worker.main.check_database_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Database unreachable"),
        ),
        patch(
            "kontexa.worker.main.check_redis_connection",
            new_callable=AsyncMock,
            side_effect=Exception("Redis connection refused"),
        ),
        patch("kontexa.worker.main.close_database_engine", new_callable=AsyncMock),
        patch("kontexa.worker.main.close_redis_connection", new_callable=AsyncMock),
    ):
        await worker.start()
        assert worker.is_running is True
        await worker.stop()
