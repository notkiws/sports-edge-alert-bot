"""Polymarket Gamma normalization for exact tennis match-winner markets."""

import json
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sports_edge.domain.polymarket import (
    PolymarketMarket,
    PolymarketTennisEvent,
    PolymarketToken,
)
from sports_edge.domain.tennis import TennisTour

SINGLES_SERIES = {TennisTour.ATP: "10365", TennisTour.WTA: "10366"}


class IneligibleTennisEvent(ValueError):
    """Raised when a Gamma event does not satisfy V1 tennis discovery rules."""


def _mapping(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return value


def _json_strings(value: object, field_name: str) -> list[str]:
    if not isinstance(value, str):
        raise IneligibleTennisEvent(f"{field_name} is missing")
    parsed: Any = json.loads(value)
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise IneligibleTennisEvent(f"{field_name} is invalid")
    return parsed


class PolymarketGammaAdapter:
    """Select the exact executable tennis match-winner market from an event."""

    def normalize_tennis_event(
        self,
        payload: Mapping[str, Any],
        tour: TennisTour,
    ) -> PolymarketTennisEvent:
        title = str(payload.get("title", ""))
        lowered_title = title.casefold()
        if "qualification" in lowered_title or "qualifying" in lowered_title:
            raise IneligibleTennisEvent("qualification events are excluded")

        series_ids = {
            str(series.get("id", ""))
            for item in payload.get("series", [])
            if (series := _mapping(item))
        }
        if SINGLES_SERIES[tour] not in series_ids:
            raise IneligibleTennisEvent("event is not in the required singles series")

        if not payload.get("active") or payload.get("closed"):
            raise IneligibleTennisEvent("event is not active")

        selected: Mapping[str, Any] | None = None
        for item in payload.get("markets", []):
            market = _mapping(item)
            if (
                market.get("question") == title
                and market.get("active") is True
                and market.get("closed") is False
                and market.get("acceptingOrders") is True
                and market.get("enableOrderBook") is True
            ):
                selected = market
                break
        if selected is None:
            raise IneligibleTennisEvent("exact active match-winner order book is unavailable")

        outcomes = _json_strings(selected.get("outcomes"), "outcomes")
        token_ids = _json_strings(selected.get("clobTokenIds"), "clobTokenIds")
        if len(outcomes) != 2 or len(token_ids) != 2:
            raise IneligibleTennisEvent("match-winner market must have exactly two outcomes")

        start_date = payload.get("startDate")
        if not isinstance(start_date, str):
            raise IneligibleTennisEvent("startDate is missing")

        return PolymarketTennisEvent(
            event_id=str(payload.get("id", "")),
            slug=str(payload.get("slug", "")),
            title=title,
            tour=tour,
            starts_at_utc=datetime.fromisoformat(start_date.replace("Z", "+00:00")),
            market=PolymarketMarket(
                market_id=str(selected.get("id", "")),
                condition_id=str(selected.get("conditionId", "")),
                question=title,
                tokens=(
                    PolymarketToken(token_id=token_ids[0], outcome=outcomes[0]),
                    PolymarketToken(token_id=token_ids[1], outcome=outcomes[1]),
                ),
            ),
        )


GammaTransport = Callable[[str], list[Mapping[str, Any]]]


class PolymarketGammaClient:
    """Discover future ATP/WTA singles events with exact match-winner books."""

    def __init__(
        self,
        *,
        transport: GammaTransport | None = None,
        base_url: str = "https://gamma-api.polymarket.com",
    ) -> None:
        self._transport = transport or self._urllib_transport
        self._base_url = base_url.rstrip("/")
        self._adapter = PolymarketGammaAdapter()

    def discover_tennis_events(
        self,
        tour: TennisTour,
        *,
        starts_after: datetime,
        limit: int = 100,
    ) -> tuple[PolymarketTennisEvent, ...]:
        if starts_after.utcoffset() != timedelta(0):
            raise ValueError("starts_after must be timezone-aware UTC")
        cutoff = starts_after.isoformat().replace("+00:00", "Z")
        query = urlencode(
            {
                "series_id": SINGLES_SERIES[tour],
                "active": "true",
                "closed": "false",
                "start_date_min": cutoff,
                "limit": limit,
                "order": "startDate",
                "ascending": "true",
            }
        )
        payloads = self._transport(f"{self._base_url}/events?{query}")
        events: list[PolymarketTennisEvent] = []
        for payload in payloads:
            raw_start = payload.get("startDate")
            if not isinstance(raw_start, str):
                continue
            event_start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
            if event_start < starts_after:
                continue
            try:
                events.append(self._adapter.normalize_tennis_event(payload, tour))
            except (IneligibleTennisEvent, json.JSONDecodeError, ValueError):
                continue
        return tuple(events)

    @staticmethod
    def _urllib_transport(url: str) -> list[Mapping[str, Any]]:
        request = Request(
            url,
            headers={
                "User-Agent": "sports-edge-alert-bot/0.1",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:
            payload: Any = json.load(response)
        if not isinstance(payload, list):
            raise ValueError("Polymarket Gamma returned a non-list payload")
        return [item for item in payload if isinstance(item, Mapping)]
