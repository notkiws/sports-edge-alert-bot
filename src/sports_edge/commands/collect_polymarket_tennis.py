"""Collect one batch of public Polymarket tennis order books."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sports_edge.collectors.polymarket_tennis import (
    PolymarketTennisForwardCollector,
    TennisCollectionResult,
)
from sports_edge.providers.polymarket_clob import PolymarketClobClient
from sports_edge.providers.polymarket_gamma import PolymarketGammaClient

DEFAULT_DESTINATION = Path("artifacts/tennis-forward/polymarket-books.jsonl")


def collect_once(
    *,
    destination: Path,
    observed_at_utc: datetime,
    gamma_client: PolymarketGammaClient | None = None,
    clob_client: PolymarketClobClient | None = None,
) -> TennisCollectionResult:
    """Run one read-only discovery and book-snapshot pass."""

    collector = PolymarketTennisForwardCollector(
        gamma_client=gamma_client or PolymarketGammaClient(),
        clob_client=clob_client or PolymarketClobClient(),
        destination=destination,
    )
    return collector.collect(observed_at_utc=observed_at_utc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect public Polymarket tennis books without alerts or trading."
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
    )
    arguments = parser.parse_args()
    result = collect_once(
        destination=arguments.destination,
        observed_at_utc=datetime.now(UTC),
    )
    print(
        json.dumps(
            {
                "events_discovered": result.events_discovered,
                "books_fetched": result.books_fetched,
                "snapshots_appended": result.snapshots_appended,
                "destination": str(arguments.destination),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
