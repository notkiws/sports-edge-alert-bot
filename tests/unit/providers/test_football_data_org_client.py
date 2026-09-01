import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

from sports_edge.providers.football_data_org_client import (
    FootballDataOrgClient,
    FootballDataOrgRequestError,
    MinimumIntervalRateLimiter,
)


class FakeTransport:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, str]]] = []

    def __call__(self, url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
        self.calls.append((url, headers))
        return self.response


def test_fetch_matches_uses_authenticated_season_endpoint() -> None:
    transport = FakeTransport({"matches": [{"id": 1}]})
    client = FootballDataOrgClient(
        api_key="test-token",
        transport=transport,
        rate_limiter=MinimumIntervalRateLimiter.disabled(),
    )

    result = client.fetch_competition_matches("PL", 2025)

    assert result == {"matches": [{"id": 1}]}
    url, headers = transport.calls[0]
    assert url.endswith("/competitions/PL/matches?season=2025")
    assert headers["X-Auth-Token"] == "test-token"


def test_rate_limiter_waits_between_requests() -> None:
    now = [100.0]
    waits: list[float] = []

    def clock() -> float:
        return now[0]

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    limiter = MinimumIntervalRateLimiter(minimum_interval_seconds=6.1, clock=clock, sleep=sleep)

    limiter.wait()
    now[0] += 2.0
    limiter.wait()

    assert waits == [pytest.approx(4.1)]


def test_cache_season_is_idempotent(tmp_path: Path) -> None:
    transport = FakeTransport({"matches": [{"id": 1}], "competition": {"code": "PL"}})
    client = FootballDataOrgClient(
        api_key="test-token",
        transport=transport,
        rate_limiter=MinimumIntervalRateLimiter.disabled(),
    )

    first = client.cache_competition_season(tmp_path, "PL", 2025)
    second = client.cache_competition_season(tmp_path, "PL", 2025)

    assert first == second
    assert len(transport.calls) == 1
    assert json.loads(first.read_text()) == transport.response


def test_http_failure_never_exposes_api_key() -> None:
    secret = "never-print-this-token"

    def failing_transport(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
        raise HTTPError(url, 401, "Unauthorized", hdrs=None, fp=None)

    client = FootballDataOrgClient(
        api_key=secret,
        transport=failing_transport,
        rate_limiter=MinimumIntervalRateLimiter.disabled(),
    )

    with pytest.raises(FootballDataOrgRequestError) as error:
        client.fetch_competition_matches("PL", 2025)

    assert secret not in str(error.value)
    assert "401" in str(error.value)


def test_retries_rate_limit_then_succeeds() -> None:
    attempts = 0
    waits: list[float] = []

    def transient_transport(url: str, headers: Mapping[str, str]) -> Mapping[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise HTTPError(url, 429, "Too Many Requests", hdrs=None, fp=None)
        return {"matches": [{"id": 1}]}

    client = FootballDataOrgClient(
        api_key="test-token",
        transport=transient_transport,
        rate_limiter=MinimumIntervalRateLimiter.disabled(),
        max_retries=2,
        retry_backoff_seconds=1.0,
        sleep=waits.append,
    )

    result = client.fetch_competition_matches("PL", 2025)

    assert result == {"matches": [{"id": 1}]}
    assert attempts == 3
    assert waits == [1.0, 2.0]
