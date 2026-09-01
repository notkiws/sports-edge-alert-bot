"""Canonical Polymarket event, market, and token entities."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from sports_edge.domain.tennis import TennisTour


@dataclass(frozen=True, slots=True)
class PolymarketToken:
    token_id: str
    outcome: str


@dataclass(frozen=True, slots=True)
class PolymarketMarket:
    market_id: str
    condition_id: str
    question: str
    tokens: tuple[PolymarketToken, PolymarketToken]


@dataclass(frozen=True, slots=True)
class PolymarketTennisEvent:
    event_id: str
    slug: str
    title: str
    tour: TennisTour
    starts_at_utc: datetime
    market: PolymarketMarket

    def __post_init__(self) -> None:
        if self.starts_at_utc.utcoffset() != timedelta(0):
            raise ValueError("starts_at_utc must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class OrderBookLevel:
    price: Decimal
    size: Decimal


@dataclass(frozen=True, slots=True)
class PolymarketOrderBook:
    market_id: str
    token_id: str
    timestamp_utc: datetime
    bids: tuple[OrderBookLevel, ...]
    asks: tuple[OrderBookLevel, ...]
    minimum_order_size: Decimal
    tick_size: Decimal

    @property
    def best_bid(self) -> Decimal | None:
        return max((level.price for level in self.bids), default=None)

    @property
    def best_ask(self) -> Decimal | None:
        return min((level.price for level in self.asks), default=None)

    @property
    def spread(self) -> Decimal | None:
        if self.best_bid is None or self.best_ask is None:
            return None
        return self.best_ask - self.best_bid

    def effective_ask_price(self, requested_size: Decimal) -> Decimal | None:
        if requested_size <= 0:
            raise ValueError("requested_size must be positive")
        remaining = requested_size
        cost = Decimal(0)
        for level in sorted(self.asks, key=lambda item: item.price):
            filled = min(remaining, level.size)
            cost += filled * level.price
            remaining -= filled
            if remaining == 0:
                return cost / requested_size
        return None
