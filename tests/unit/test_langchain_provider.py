"""Tests for the LangChain-backed structured model provider (RESPX-mocked, no network).

A real ``ChatOpenAI`` is driven against a mocked OpenAI-compatible ``/chat/completions`` endpoint so
the function-calling structured-output contract is exercised end to end without credentials.
"""

from typing import Any

import httpx
import respx
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from bicho.domain.ports.model_provider import RunMeta
from bicho.infrastructure.model.provider import (
    LangChainModelProvider,
    _message_text,
    _run_config,
)
from bicho.infrastructure.model.registry import (
    ModelSpec,
    build_chat_model,
    build_model_provider,
)

_BASE_URL = "https://test.minimax.local/v1"
_META = RunMeta(role="analyzer", prompt_version="v1", correlation_id="corr-1", tags=("extra",))


class Answer(BaseModel):
    """A structured answer used to exercise function-calling output."""

    summary: str
    score: int


def _completion(tool_arguments: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-x",
        "object": "chat.completion",
        "created": 0,
        "model": "MiniMax-M3",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "Answer", "arguments": tool_arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _provider() -> LangChainModelProvider:
    return build_model_provider(
        ModelSpec(model="MiniMax-M3", api_key="test-key", base_url=_BASE_URL)
    )


@respx.mock
async def test_structured_returns_validated_value() -> None:
    respx.post(f"{_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion('{"summary": "ok", "score": 3}'))
    )
    result = await _provider().structured(prompt="review this", schema=Answer, meta=_META)

    assert result.ok
    assert result.value == Answer(summary="ok", score=3)
    assert result.model_id == "MiniMax-M3"


@respx.mock
async def test_structured_reports_parse_error_as_data() -> None:
    respx.post(f"{_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=_completion('{"summary": "missing score"}'))
    )
    result = await _provider().structured(prompt="p", schema=Answer, meta=_META)

    assert not result.ok
    assert result.value is None
    assert result.error is not None


@respx.mock
async def test_structured_reports_transport_error_as_data() -> None:
    respx.post(f"{_BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": {"message": "boom"}})
    )
    result = await _provider().structured(prompt="p", schema=Answer, meta=_META)

    assert not result.ok
    assert result.value is None
    assert result.error is not None


def test_run_config_carries_tracing_tags() -> None:
    config = _run_config(_META)

    assert config["run_name"] == "analyzer"
    assert set(config["tags"]) >= {"extra", "role:analyzer", "prompt:v1"}
    assert config["metadata"]["correlation_id"] == "corr-1"


def test_message_text_extracts_content_or_none() -> None:
    assert _message_text(None) is None
    assert _message_text(AIMessage(content="hi")) == "hi"


def test_build_chat_model_targets_the_configured_endpoint() -> None:
    model = build_chat_model(
        ModelSpec(model="MiniMax-M3", api_key="k", base_url=_BASE_URL, timeout_seconds=5)
    )

    assert model.model_name == "MiniMax-M3"
    assert str(model.openai_api_base) == _BASE_URL


def test_build_model_provider_wires_model_id() -> None:
    provider = build_model_provider(ModelSpec(model="MiniMax-M3", api_key="k", base_url=_BASE_URL))

    assert isinstance(provider, LangChainModelProvider)
    assert provider._model_id == "MiniMax-M3"
