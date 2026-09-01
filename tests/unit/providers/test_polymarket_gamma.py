from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest

from sports_edge.domain.tennis import TennisTour
from sports_edge.providers.polymarket_gamma import (
    IneligibleTennisEvent,
    PolymarketGammaAdapter,
    PolymarketGammaClient,
)


def event_payload() -> dict[str, object]:
    title = "US Open ATP: Ben Shelton vs Hubert Hurkacz"
    return {
        "id": "945997",
        "slug": "us-open-atp-ben-shelton-vs-hubert-hurkacz",
        "title": title,
        "startDate": "2026-09-01T17:00:00Z",
        "active": True,
        "closed": False,
        "series": [{"id": "10365"}],
        "markets": [
            {
                "id": "prop-1",
                "question": "Set 1 Winner: Shelton vs Hurkacz",
                "outcomes": '["Shelton", "Hurkacz"]',
                "clobTokenIds": '["set-token-1", "set-token-2"]',
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "enableOrderBook": True,
            },
            {
                "id": "match-1",
                "conditionId": "condition-1",
                "question": title,
                "outcomes": '["Ben Shelton", "Hubert Hurkacz"]',
                "clobTokenIds": '["player-token-1", "player-token-2"]',
                "active": True,
                "closed": False,
                "acceptingOrders": True,
                "enableOrderBook": True,
            },
        ],
    }


def test_normalizes_only_exact_match_winner_contract() -> None:
    event = PolymarketGammaAdapter().normalize_tennis_event(event_payload(), TennisTour.ATP)

    assert event.event_id == "945997"
    assert event.tour is TennisTour.ATP
    assert event.starts_at_utc == datetime(2026, 9, 1, 17, 0, tzinfo=UTC)
    assert event.market.market_id == "match-1"
    assert [(token.outcome, token.token_id) for token in event.market.tokens] == [
        ("Ben Shelton", "player-token-1"),
        ("Hubert Hurkacz", "player-token-2"),
    ]


def test_rejects_qualification_event() -> None:
    payload = event_payload()
    payload["title"] = "US Open Qualification ATP: Player One vs Player Two"

    with pytest.raises(IneligibleTennisEvent, match="qualification"):
        PolymarketGammaAdapter().normalize_tennis_event(payload, TennisTour.ATP)


def test_rejects_doubles_series_even_when_primary_tag_matches() -> None:
    payload = event_payload()
    payload["series"] = [{"id": "11632"}]

    with pytest.raises(IneligibleTennisEvent, match="singles series"):
        PolymarketGammaAdapter().normalize_tennis_event(payload, TennisTour.ATP)


def test_rejects_event_without_exact_active_order_book() -> None:
    payload = event_payload()
    payload["markets"][1]["acceptingOrders"] = False  # type: ignore[index]

    with pytest.raises(IneligibleTennisEvent, match="match-winner"):
        PolymarketGammaAdapter().normalize_tennis_event(payload, TennisTour.ATP)


def test_discovers_future_atp_singles_with_server_and_client_cutoffs() -> None:
    stale = event_payload()
    stale["id"] = "stale"
    stale["startDate"] = "2026-09-01T10:00:00Z"
    valid = event_payload()
    captured_urls: list[str] = []

    def transport(url: str) -> list[dict[str, object]]:
        captured_urls.append(url)
        return [stale, valid]

    client = PolymarketGammaClient(transport=transport)
    events = client.discover_tennis_events(
        TennisTour.ATP,
        starts_after=datetime(2026, 9, 1, 12, 0, tzinfo=UTC),
    )

    assert [event.event_id for event in events] == ["945997"]
    query = parse_qs(urlparse(captured_urls[0]).query)
    assert query["series_id"] == ["10365"]
    assert query["start_date_min"] == ["2026-09-01T12:00:00Z"]
    assert query["active"] == ["true"]
    assert query["closed"] == ["false"]
