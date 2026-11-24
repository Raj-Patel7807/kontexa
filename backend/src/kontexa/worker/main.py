"""Background worker process entrypoint for Kontexa.

The worker executes long-running asynchronous background jobs—such as
repository synchronization, AST symbol parsing, document chunking and
embeddings generation, and sandboxed task execution—outside the HTTP request lifecycle.
"""

import asyncio
import logging
import signal
import sys
from collections.abc import Callable

from kontexa.core.config import settings
from kontexa.database.redis import check_redis_connection, close_redis_connection
from kontexa.database.session import check_database_connection, close_database_engine

logger = logging.getLogger(__name__)


class WorkerService:
    """Manages background task queue polling, job execution, and graceful shutdown."""

    def __init__(self) -> None:
        self.is_running: bool = False
        self._shutdown_event: asyncio.Event = asyncio.Event()

    async def start(self) -> None:
        """Initialize worker state, verify infrastructure connectivity, and begin polling."""
        logger.info(
            "Starting %s background worker in %s environment...",
            settings.app_name,
            settings.app_env,
        )

        # Verify dependency reachability on startup
        try:
            await check_database_connection()
            logger.info("Worker database connection verified.")
        except Exception as exc:
            logger.warning("Worker database connection degraded on startup: %s", exc)

        try:
            await check_redis_connection()
            logger.info("Worker Redis queue connection verified.")
        except Exception as exc:
            logger.warning("Worker Redis queue connection degraded on startup: %s", exc)

        self.is_running = True
        logger.info("Worker service ready for background jobs.")

    async def stop(self) -> None:
        """Trigger graceful shutdown and clean up shared connection pools."""
        if not self.is_running:
            return

        logger.info("Shutting down worker service...")
        self.is_running = False
        self._shutdown_event.set()

        await close_redis_connection()
        await close_database_engine()
        logger.info("Worker service terminated cleanly.")

    async def run(self, max_iterations: int | None = None) -> None:
        """Execute the worker polling loop until stopped or maximum iterations reached."""
        await self.start()
        iteration = 0

        while self.is_running and not self._shutdown_event.is_set():
            iteration += 1
            logger.debug("Worker heartbeat iteration %d", iteration)

            if max_iterations is not None and iteration >= max_iterations:
                logger.info("Worker reached max iterations (%d). Stopping loop.", max_iterations)
                break

            try:
                # Sleep in short slices to respond quickly to shutdown events
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=1.0)
            except TimeoutError:
                # Normal timeout: proceed to next polling iteration
                pass
            except asyncio.CancelledError:
                logger.info("Worker polling loop received cancellation.")
                break

        await self.stop()


def setup_signal_handlers(shutdown_callback: Callable[[], None]) -> None:
    """Register OS termination signal handlers for graceful shutdown."""
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, shutdown_callback)


async def main() -> None:
    """Application entrypoint for running the worker process."""
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    worker = WorkerService()

    def handle_shutdown() -> None:
        logger.info("Received termination signal.")
        asyncio.create_task(worker.stop())

    setup_signal_handlers(handle_shutdown)

    try:
        await worker.run()
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Worker interrupted by user.")
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
