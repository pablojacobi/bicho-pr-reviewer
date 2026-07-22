"""GitHub App authentication: an app JWT exchanged for a cached installation access token.

The app JWT is RS256-signed with the app's private key (``iat`` back-dated to absorb clock drift,
``exp`` within GitHub's 10-minute limit). Installation tokens (~1h) are cached until near expiry.
"""

from dataclasses import dataclass
from datetime import datetime

import httpx
import jwt

from bicho.domain.ports.system import Clock

_JWT_LIFETIME_SECONDS = 540
_REFRESH_MARGIN_SECONDS = 60


@dataclass(frozen=True)
class _CachedToken:
    token: str
    expires_at: float


class GitHubAppAuth:
    """Signs app JWTs and exchanges them for installation tokens, cached until near expiry."""

    def __init__(
        self,
        *,
        app_id: str,
        private_key: str,
        clock: Clock,
        http: httpx.AsyncClient,
        api_base: str = "https://api.github.com",
    ) -> None:
        self._app_id = app_id
        self._private_key = private_key
        self._clock = clock
        self._http = http
        self._api_base = api_base.rstrip("/")
        self._cache: dict[int, _CachedToken] = {}

    def app_jwt(self) -> str:
        """Return a short-lived RS256 JWT identifying the GitHub App."""
        issued = int(self._clock.now().timestamp())
        payload = {
            "iat": issued - _REFRESH_MARGIN_SECONDS,
            "exp": issued + _JWT_LIFETIME_SECONDS,
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    async def installation_token(self, installation_id: int) -> str:
        """Return a valid installation access token, refreshing it when near expiry."""
        now = self._clock.now().timestamp()
        cached = self._cache.get(installation_id)
        if cached is not None and cached.expires_at > now + _REFRESH_MARGIN_SECONDS:
            return cached.token
        response = await self._http.post(
            f"{self._api_base}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self.app_jwt()}",
                "Accept": "application/vnd.github+json",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._cache[installation_id] = _CachedToken(
            token=data["token"], expires_at=datetime.fromisoformat(data["expires_at"]).timestamp()
        )
        return data["token"]
