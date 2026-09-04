"""Rate-limited football-data.org HTTP collection and raw caching."""

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

Transport = Callable[[str, Mapping[str, str]], Mapping[str, Any]]


class FootballDataOrgRequestError(RuntimeError):
    """A token-safe football-data.org request failure."""


@dataclass(slots=True)
class MinimumIntervalRateLimiter:
    """Enforce a minimum delay between request start times."""

    minimum_interval_seconds: float
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    _last_request_at: float | None = field(default=None, init=False)

    @classmethod
    def disabled(cls) -> "MinimumIntervalRateLimiter":
        return cls(minimum_interval_seconds=0.0)

    def wait(self) -> None:
        now = self.clock()
        if self._last_request_at is not None:
            remaining = self.minimum_interval_seconds - (now - self._last_request_at)
            if remaining > 0:
                self.sleep(remaining)
                now = self.clock()
        self._last_request_at = now


class FootballDataOrgClient:
    """Read-only football-data.org client for verified free competitions."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: Transport | None = None,
        rate_limiter: MinimumIntervalRateLimiter | None = None,
        base_url: str = "https://api.football-data.org/v4",
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("football-data.org API key is required")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self._api_key = api_key
        self._transport = transport or self._urllib_transport
        self._rate_limiter = rate_limiter or MinimumIntervalRateLimiter(6.1)
        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds
        self._sleep = sleep

    def fetch_competition_matches(self, competition_code: str, season: int) -> Mapping[str, Any]:
        query = urlencode({"season": season})
        return self._get(f"/competitions/{competition_code}/matches?{query}")

    def fetch_competition_matches_between(
        self,
        competition_code: str,
        date_from: date,
        date_to: date,
    ) -> Mapping[str, Any]:
        """Fetch a refreshable fixture window without caching stale statuses."""

        if date_from > date_to:
            raise ValueError("date_from must not be after date_to")
        query = urlencode(
            {
                "dateFrom": date_from.isoformat(),
                "dateTo": date_to.isoformat(),
            }
        )
        return self._get(f"/competitions/{competition_code}/matches?{query}")

    def cache_competition_season(
        self,
        cache_root: Path,
        competition_code: str,
        season: int,
    ) -> Path:
        destination = cache_root / str(season) / f"{competition_code}.json"
        if destination.exists():
            return destination
        payload = self.fetch_competition_matches(competition_code, season)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        temporary.replace(destination)
        return destination

    def _get(self, path: str) -> Mapping[str, Any]:
        url = f"{self._base_url}{path}"
        headers = {
            "X-Auth-Token": self._api_key,
            "User-Agent": "sports-edge-alert-bot/0.1",
            "Accept": "application/json",
        }
        for attempt in range(self._max_retries + 1):
            self._rate_limiter.wait()
            try:
                return self._transport(url, headers)
            except HTTPError as error:
                transient = error.code == 429 or 500 <= error.code < 600
                if transient and attempt < self._max_retries:
                    self._sleep(self._retry_backoff_seconds * (2**attempt))
                    continue
                raise FootballDataOrgRequestError(
                    f"football-data.org request failed with HTTP {error.code}"
                ) from error
            except URLError as error:
                raise FootballDataOrgRequestError("football-data.org request failed") from error
        raise AssertionError("retry loop exited unexpectedly")

    @staticmethod
    def _urllib_transport(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
        request = Request(url, headers=dict(headers))
        with urlopen(request, timeout=30) as response:
            payload: Any = json.load(response)
        if not isinstance(payload, Mapping):
            raise FootballDataOrgRequestError("football-data.org returned a non-object payload")
        return payload
