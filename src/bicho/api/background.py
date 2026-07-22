"""In-process background execution for webhook-triggered reviews.

A webhook is acknowledged at once (202) and the review runs off-request as an asyncio task. This is
deliberately **non-durable**: a restart drops an accepted-but-unfinished review (documented, and
recovered via the manual endpoint). A semaphore bounds concurrency (default 1, matching the single
instance), and every task is isolated so one failure never touches another or the process.
``RecentDeliveries`` short-circuits duplicate deliveries without any datastore.
"""

import asyncio
from collections import deque
from typing import Protocol

import structlog

from bicho.application.review_service import ReviewService
from bicho.domain.models.review import ReviewOptions, ReviewRequest

_logger = structlog.get_logger(__name__)


class ReviewServiceProvider(Protocol):
    """Supplies the review service for an installation (implemented by the container)."""

    def review_service(self, installation_id: int | None = None) -> ReviewService: ...


class RecentDeliveries:
    """A bounded, in-memory set of seen delivery ids, evicting oldest-first past ``max_size``."""

    def __init__(self, *, max_size: int = 2048) -> None:
        self._max_size = max_size
        self._seen: set[str] = set()
        self._order: deque[str] = deque()

    def register(self, delivery_id: str) -> bool:
        """Record ``delivery_id``; return ``True`` if new, ``False`` if already seen."""
        if delivery_id in self._seen:
            return False
        self._seen.add(delivery_id)
        self._order.append(delivery_id)
        if len(self._order) > self._max_size:
            self._seen.discard(self._order.popleft())
        return True


class BackgroundReviewRunner:
    """Schedules reviews as isolated, concurrency-bounded asyncio tasks."""

    def __init__(self, provider: ReviewServiceProvider, *, concurrency: int = 1) -> None:
        self._provider = provider
        self._semaphore = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()
        self.deliveries = RecentDeliveries()

    def schedule(self, request: ReviewRequest, options: ReviewOptions) -> None:
        """Start a background review; returns immediately."""
        task = asyncio.create_task(self._run(request, options))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, request: ReviewRequest, options: ReviewOptions) -> None:
        async with self._semaphore:
            try:
                service = self._provider.review_service(request.installation_id)
                await service.run(request, options)
            except Exception:
                _logger.exception(
                    "background_review_failed",
                    repository=request.repository,
                    pr_number=request.pr_number,
                )

    async def drain(self) -> None:
        """Await all in-flight reviews (used on shutdown and in tests)."""
        while self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
