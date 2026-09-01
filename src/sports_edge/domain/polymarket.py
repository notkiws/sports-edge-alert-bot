"""Canonical Polymarket event, market, and token entities."""

from dataclasses import dataclass
from datetime import datetime, timedelta

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
