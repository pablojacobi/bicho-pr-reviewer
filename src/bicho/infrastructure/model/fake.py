"""A deterministic ``ModelProvider`` fake for tests and offline runs.

It returns pre-scripted results in order and records each call, so tests can drive success, invalid
output, and error paths without any network or credentials.
"""

from collections.abc import Sequence
from typing import Any, cast

from pydantic import BaseModel

from bicho.domain.ports.model_provider import ModelResult, RunMeta, error_result


class FakeModelProvider:
    """Returns pre-scripted ``ModelResult``s in order and records each call's metadata."""

    def __init__(
        self, results: Sequence[ModelResult[Any]] = (), *, model_id: str = "fake-model"
    ) -> None:
        self._results = list(results)
        self._model_id = model_id
        self.calls: list[RunMeta] = []

    async def structured[T: BaseModel](
        self, *, prompt: str, schema: type[T], meta: RunMeta
    ) -> ModelResult[T]:
        self.calls.append(meta)
        if not self._results:
            return error_result("no scripted response", model_id=self._model_id)
        return cast(ModelResult[T], self._results.pop(0))
