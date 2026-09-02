"""Read-only Polymarket tennis order-book snapshot collection."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from sports_edge.domain.tennis import TennisTour
from sports_edge.providers.polymarket_clob import PolymarketClobClient
from sports_edge.providers.polymarket_gamma import PolymarketGammaClient
from sports_edge.storage.tennis_forward import append_polymarket_book_snapshot


@dataclass(frozen=True, slots=True)
class TennisCollectionResult:
    events_discovered: int
    books_fetched: int
    snapshots_appended: int


class PolymarketTennisForwardCollector:
    """Discover eligible events and persist both public outcome books."""

    def __init__(
        self,
        *,
        gamma_client: PolymarketGammaClient,
        clob_client: PolymarketClobClient,
        destination: Path,
    ) -> None:
        self._gamma_client = gamma_client
        self._clob_client = clob_client
        self._destination = destination

    def collect(self, *, observed_at_utc: datetime) -> TennisCollectionResult:
        if observed_at_utc.utcoffset() != timedelta(0):
            raise ValueError("observed_at_utc must be timezone-aware UTC")
        events = tuple(
            event
            for tour in (TennisTour.ATP, TennisTour.WTA)
            for event in self._gamma_client.discover_tennis_events(
                tour,
                starts_after=observed_at_utc,
            )
        )
        books_fetched = 0
        snapshots_appended = 0
        for event in events:
            for token in event.market.tokens:
                book = self._clob_client.fetch_order_book(token.token_id)
                books_fetched += 1
                if (
                    book.market_id != event.market.market_id
                    or book.token_id != token.token_id
                ):
                    raise ValueError("CLOB book does not match the discovered market token")
                snapshots_appended += int(
                    append_polymarket_book_snapshot(
                        self._destination,
                        event,
                        book,
                        observed_at_utc,
                    )
                )
        return TennisCollectionResult(
            events_discovered=len(events),
            books_fetched=books_fetched,
            snapshots_appended=snapshots_appended,
        )
