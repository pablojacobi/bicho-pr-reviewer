"""Tests for the model provider port, result type, and deterministic fake."""

from pydantic import BaseModel

from bicho.domain.ports.model_provider import ModelProvider, RunMeta, error_result, ok_result
from bicho.infrastructure.model.fake import FakeModelProvider


class _Schema(BaseModel):
    value: int


def _meta() -> RunMeta:
    return RunMeta(role="security", prompt_version="v1", correlation_id="corr-1")


def test_ok_result_carries_the_value() -> None:
    result = ok_result(_Schema(value=1), model_id="m")

    assert result.ok is True
    assert result.value == _Schema(value=1)
    assert result.error is None


def test_error_result_carries_the_error() -> None:
    result = error_result("boom", model_id="m", raw="{bad json")

    assert result.ok is False
    assert result.value is None
    assert result.error == "boom"
    assert result.raw == "{bad json"


async def test_fake_returns_the_scripted_result() -> None:
    provider: ModelProvider = FakeModelProvider(
        [ok_result(_Schema(value=42), model_id="fake-model")]
    )

    result = await provider.structured(prompt="p", schema=_Schema, meta=_meta())

    assert result.ok is True
    assert result.value == _Schema(value=42)


async def test_fake_records_each_call() -> None:
    provider = FakeModelProvider([ok_result(_Schema(value=1), model_id="x")])

    await provider.structured(prompt="p", schema=_Schema, meta=_meta())

    assert provider.calls[0].role == "security"


async def test_fake_fails_when_no_scripted_results_remain() -> None:
    provider = FakeModelProvider()

    result = await provider.structured(prompt="p", schema=_Schema, meta=_meta())

    assert result.ok is False
    assert result.error is not None
    assert "no scripted response" in result.error
