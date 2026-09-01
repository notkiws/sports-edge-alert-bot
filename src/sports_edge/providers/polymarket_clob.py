"""Polymarket CLOB order-book normalization."""

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sports_edge.domain.polymarket import OrderBookLevel, PolymarketOrderBook


class InvalidOrderBook(ValueError):
    """Raised when required CLOB order-book fields are invalid."""


def _levels(value: object, side: str) -> tuple[OrderBookLevel, ...]:
    if not isinstance(value, list):
        raise InvalidOrderBook(f"{side} must be a list")
    levels: list[OrderBookLevel] = []
    try:
        for item in value:
            if not isinstance(item, Mapping):
                raise InvalidOrderBook(f"{side} level must be an object")
            price = Decimal(str(item.get("price", "")))
            size = Decimal(str(item.get("size", "")))
            if not Decimal(0) < price < Decimal(1) or size <= 0:
                raise InvalidOrderBook(f"{side} level has invalid price or size")
            levels.append(OrderBookLevel(price=price, size=size))
    except InvalidOperation as error:
        raise InvalidOrderBook(f"{side} level is not numeric") from error
    return tuple(levels)


class PolymarketClobAdapter:
    """Convert a CLOB `/book` response into a canonical order book."""

    def normalize_order_book(self, payload: Mapping[str, Any]) -> PolymarketOrderBook:
        try:
            timestamp_utc = datetime.fromtimestamp(
                int(str(payload.get("timestamp", ""))) / 1000,
                tz=UTC,
            )
            minimum_order_size = Decimal(str(payload.get("min_order_size", "")))
            tick_size = Decimal(str(payload.get("tick_size", "")))
        except (InvalidOperation, ValueError) as error:
            raise InvalidOrderBook("order-book metadata is invalid") from error

        return PolymarketOrderBook(
            market_id=str(payload.get("market", "")),
            token_id=str(payload.get("asset_id", "")),
            timestamp_utc=timestamp_utc,
            bids=_levels(payload.get("bids"), "bids"),
            asks=_levels(payload.get("asks"), "asks"),
            minimum_order_size=minimum_order_size,
            tick_size=tick_size,
        )


ClobTransport = Callable[[str], Mapping[str, Any]]


class PolymarketClobClient:
    """Fetch public CLOB order books by outcome token ID."""

    def __init__(
        self,
        *,
        transport: ClobTransport | None = None,
        base_url: str = "https://clob.polymarket.com",
    ) -> None:
        self._transport = transport or self._urllib_transport
        self._base_url = base_url.rstrip("/")
        self._adapter = PolymarketClobAdapter()

    def fetch_order_book(self, token_id: str) -> PolymarketOrderBook:
        query = urlencode({"token_id": token_id})
        payload = self._transport(f"{self._base_url}/book?{query}")
        return self._adapter.normalize_order_book(payload)

    @staticmethod
    def _urllib_transport(url: str) -> Mapping[str, Any]:
        request = Request(
            url,
            headers={
                "User-Agent": "sports-edge-alert-bot/0.1",
                "Accept": "application/json",
            },
        )
        with urlopen(request, timeout=30) as response:
            payload: Any = json.load(response)
        if not isinstance(payload, Mapping):
            raise InvalidOrderBook("Polymarket CLOB returned a non-object payload")
        return payload
