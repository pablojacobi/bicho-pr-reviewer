"""Tests for the background review runner and delivery de-duplication."""

from typing import cast

from bicho.api.background import BackgroundReviewRunner, RecentDeliveries
from bicho.application.review_service import ReviewService
from bicho.domain.models.review import ReviewOptions, ReviewRequest


def test_recent_deliveries_flags_duplicates() -> None:
    deliveries = RecentDeliveries()

    assert deliveries.register("a") is True
    assert deliveries.register("a") is False


def test_recent_deliveries_evicts_oldest_past_capacity() -> None:
    deliveries = RecentDeliveries(max_size=2)
    deliveries.register("a")
    deliveries.register("b")
    deliveries.register("c")  # evicts "a"

    assert deliveries.register("a") is True  # "a" was evicted, so it looks new again
    assert deliveries.register("c") is False  # "c" is still remembered


class _RecordingService:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[ReviewRequest] = []
        self._fail = fail

    async def run(self, request: ReviewRequest, options: ReviewOptions) -> None:
        self.calls.append(request)
        if self._fail:
            raise RuntimeError("boom")


class _Provider:
    def __init__(self, service: _RecordingService) -> None:
        self._service = service

    def review_service(self, installation_id: int | None = None) -> ReviewService:
        return cast(ReviewService, self._service)


def _request() -> ReviewRequest:
    return ReviewRequest(repository="o/r", pr_number=1)


async def test_runner_runs_a_scheduled_review() -> None:
    service = _RecordingService()
    runner = BackgroundReviewRunner(_Provider(service))

    runner.schedule(_request(), ReviewOptions())
    await runner.drain()

    assert len(service.calls) == 1


async def test_runner_isolates_a_failing_review() -> None:
    service = _RecordingService(fail=True)
    runner = BackgroundReviewRunner(_Provider(service))

    runner.schedule(_request(), ReviewOptions())
    await runner.drain()  # must not raise despite the failure

    assert len(service.calls) == 1


async def test_drain_with_no_tasks_is_a_noop() -> None:
    runner = BackgroundReviewRunner(_Provider(_RecordingService()))

    await runner.drain()
