"""Full webhook-to-publish e2e: a signed webhook drives a real background review that publishes.

The FastAPI app runs with its real lifespan-built runner and container; only the outbound GitHub and
MiniMax calls are RESPX-mocked. After acknowledging the webhook we drain the background runner and
assert a review was published.
"""

import hashlib
import hmac
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
_SECRET = "s3cret"
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
            app_id="1",
            private_key=SecretStr(_KEY),
            installation_id=0,
            api_base=_GH,
            webhook_secret=SecretStr(_SECRET),
        ),
        llm=LLMSettings(api_key=SecretStr("k"), base_url=_LLM, model="MiniMax-M3"),
        scanner=ScannerSettings(semgrep_enabled=False),
    )


def _chat_completion() -> dict[str, Any]:
    arguments = json.dumps(
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
                            "function": {"name": "AnalyzerReport", "arguments": arguments},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _mock_endpoints() -> respx.Route:
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
    respx.get(f"{_GH}/repos/o/r/pulls/1/reviews").mock(return_value=httpx.Response(200, json=[]))
    respx.post(f"{_LLM}/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_completion())
    )
    return respx.post(f"{_GH}/repos/o/r/pulls/1/reviews").mock(
        return_value=httpx.Response(200, json={"id": 999})
    )


def _payload() -> bytes:
    return json.dumps(
        {
            "action": "opened",
            "pull_request": {"number": 1, "draft": False, "head": {"sha": "sha"}},
            "repository": {"full_name": "o/r"},
            "installation": {"id": 7},
        }
    ).encode()


@respx.mock
async def test_signed_webhook_publishes_a_review() -> None:
    publish = _mock_endpoints()
    body = _payload()
    signature = "sha256=" + hmac.new(_SECRET.encode(), body, hashlib.sha256).hexdigest()
    app = create_app(_settings())

    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/webhooks/github",
                content=body,
                headers={
                    "X-Hub-Signature-256": signature,
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "d1",
                },
            )
        assert response.status_code == 202
        await app.state.review_runner.drain()

    assert publish.called
