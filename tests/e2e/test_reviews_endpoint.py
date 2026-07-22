"""End-to-end test for ``POST /reviews`` (dry-run) with GitHub and MiniMax both RESPX-mocked.

Exercises the real composition root: a request flows through the FastAPI app, the container-built
``ReviewService``, the GitHub client (App token + PR + files) and the LangChain provider (function
calling), and comes back as a composed draft — all without network or credentials.
"""

import json
from typing import Any

import httpx
import respx
from asgi_lifespan import LifespanManager
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from bicho.api.app import create_app
from bicho.config.settings import GitHubSettings, LLMSettings, ScannerSettings, Settings

_GH = "https://gh.test/api"
_LLM = "https://llm.test/v1"
_PATCH = "@@ -10,3 +10,4 @@\n ctx\n-old\n+new_a\n+new_b\n"


def _private_key() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


_KEY = _private_key()


def _settings() -> Settings:
    return Settings(
        github=GitHubSettings(
            app_id="1", private_key=SecretStr(_KEY), installation_id=7, api_base=_GH
        ),
        llm=LLMSettings(api_key=SecretStr("k"), base_url=_LLM, model="MiniMax-M3"),
        scanner=ScannerSettings(semgrep_enabled=False),
    )


def _analyzer_report() -> str:
    return json.dumps(
        {
            "findings": [
                {
                    "title": "Off-by-one",
                    "explanation": "e",
                    "impact": "i",
                    "recommendation": "r",
                    "path": "app/db.py",
                    "start_line": 11,
                    "end_line": 11,
                    "severity": "high",
                    "confidence": "high",
                    "subcategory": "off-by-one",
                    "snippet": "new_a",
                }
            ]
        }
    )


def _chat_completion(tool_arguments: str) -> dict[str, Any]:
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
                            "function": {"name": "AnalyzerReport", "arguments": tool_arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _mock_github_and_model() -> None:
    respx.post(f"{_GH}/app/installations/7/access_tokens").mock(
        return_value=httpx.Response(
            201, json={"token": "tok", "expires_at": "2999-01-01T00:00:00Z"}
        )
    )
    respx.get(f"{_GH}/repos/o/r/pulls/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "number": 1,
                "title": "T",
                "body": "",
                "draft": False,
                "head": {"sha": "sha"},
                "base": {"ref": "main", "repo": {"full_name": "o/r"}},
                "user": {"login": "alice"},
            },
        )
    )
    respx.get(url__startswith=f"{_GH}/repos/o/r/pulls/1/files").mock(
        return_value=httpx.Response(
            200, json=[{"filename": "app/db.py", "status": "modified", "patch": _PATCH}]
        )
    )
    respx.get(url__startswith=f"{_GH}/repos/o/r/contents/app/db.py").mock(
        return_value=httpx.Response(200, text="def f():\n    return 1\n")
    )
    respx.post(f"{_LLM}/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_completion(_analyzer_report()))
    )


@respx.mock
async def test_post_reviews_dry_run_returns_composed_draft() -> None:
    _mock_github_and_model()
    app = create_app(_settings())
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/reviews", json={"repository": "o/r", "pr_number": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "dry_run"
    # The container runs the full analyzer set; each returns the same canned finding under its own
    # category, so counts are >= 1 (this test proves the HTTP wiring, not the analyzer logic).
    assert body["total_count"] >= 1
    assert body["confirmed_count"] >= 1
    assert body["draft"]["inline_comments"][0]["path"] == "app/db.py"
