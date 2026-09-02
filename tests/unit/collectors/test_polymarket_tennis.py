import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sports_edge.collectors.polymarket_tennis import PolymarketTennisForwardCollector
from sports_edge.commands.collect_polymarket_tennis import collect_once
from sports_edge.providers.polymarket_clob import PolymarketClobClient
from sports_edge.providers.polymarket_gamma import PolymarketGammaClient


def gamma_transport(url: str):
    series_id = parse_qs(urlparse(url).query)["series_id"][0]
    if series_id != "10365":
        return []
    title = "Novak Djokovic vs Carlos Alcaraz"
    return [
        {
            "id": "event-1",
            "slug": "djokovic-alcaraz",
            "title": title,
            "startDate": "2026-09-10T12:00:00Z",
            "active": True,
            "closed": False,
            "series": [{"id": "10365"}],
            "markets": [
                {
                    "id": "market-1",
                    "conditionId": "condition-1",
                    "question": title,
                    "active": True,
                    "closed": False,
                    "acceptingOrders": True,
                    "enableOrderBook": True,
                    "outcomes": '["Novak Djokovic", "Carlos Alcaraz"]',
                    "clobTokenIds": '["token-djokovic", "token-alcaraz"]',
                }
            ],
        }
    ]


def clob_transport(url: str):
    token_id = parse_qs(urlparse(url).query)["token_id"][0]
    return {
        "market": "market-1",
        "asset_id": token_id,
        "timestamp": "1789034370000",
        "min_order_size": "5",
        "tick_size": "0.01",
        "bids": [{"price": "0.49", "size": "100"}],
        "asks": [{"price": "0.51", "size": "100"}],
    }


def test_collector_discovers_both_tokens_and_deduplicates_unchanged_books(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "polymarket-tennis-books.jsonl"
    collector = PolymarketTennisForwardCollector(
        gamma_client=PolymarketGammaClient(transport=gamma_transport),
        clob_client=PolymarketClobClient(transport=clob_transport),
        destination=destination,
    )
    observed_at = datetime(2026, 9, 10, 10, tzinfo=UTC)

    first = collector.collect(observed_at_utc=observed_at)
    second = collector.collect(observed_at_utc=observed_at)

    assert first.events_discovered == 1
    assert first.books_fetched == 2
    assert first.snapshots_appended == 2
    assert second.snapshots_appended == 0
    rows = [json.loads(line) for line in destination.read_text().splitlines()]
    assert {row["token_id"] for row in rows} == {
        "token-djokovic",
        "token-alcaraz",
    }
    assert all(row["qualified"] is False for row in rows)
    assert all(row["rejection_reasons"] == ["MODEL_NOT_EVALUATED"] for row in rows)


def test_collect_once_wires_read_only_clients_to_destination(tmp_path: Path) -> None:
    result = collect_once(
        destination=tmp_path / "books.jsonl",
        observed_at_utc=datetime(2026, 9, 10, 10, tzinfo=UTC),
        gamma_client=PolymarketGammaClient(transport=gamma_transport),
        clob_client=PolymarketClobClient(transport=clob_transport),
    )

    assert result.snapshots_appended == 2
