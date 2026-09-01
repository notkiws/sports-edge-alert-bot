import os
from datetime import UTC, datetime

import pytest

from sports_edge.domain.tennis import TennisTour
from sports_edge.providers.polymarket_gamma import PolymarketGammaClient


def test_live_discovers_only_future_tennis_match_winner_books() -> None:
    if os.getenv("RUN_LIVE_POLYMARKET_CONTRACTS") != "1":
        pytest.skip("RUN_LIVE_POLYMARKET_CONTRACTS is not enabled")

    cutoff = datetime.now(UTC)
    client = PolymarketGammaClient()
    events = tuple(
        event
        for tour in (TennisTour.ATP, TennisTour.WTA)
        for event in client.discover_tennis_events(tour, starts_after=cutoff)
    )

    assert all(event.starts_at_utc >= cutoff for event in events)
    assert all(event.market.question == event.title for event in events)
    assert all(len(event.market.tokens) == 2 for event in events)
