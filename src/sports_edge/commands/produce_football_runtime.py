"""Produce qualified football forecasts for the unsent report scheduler."""

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sports_edge.providers.football_data_org import VERIFIED_FREE_COMPETITIONS
from sports_edge.providers.football_data_org_client import FootballDataOrgClient
from sports_edge.runtime.football import (
    collect_upcoming_fixtures,
    load_historical_matches,
    produce_runtime_forecasts,
    write_runtime_forecasts,
)


def produce(
    *,
    history_root: Path,
    output_path: Path,
    raw_snapshot_root: Path,
    horizon_days: int,
    now_utc: datetime,
) -> dict[str, object]:
    """Run one read-only provider/model/report-input cycle."""

    if horizon_days < 1 or horizon_days > 10:
        raise ValueError("horizon_days must be between 1 and 10")
    if now_utc.utcoffset() != timedelta(0):
        raise ValueError("now_utc must be timezone-aware UTC")
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        raise RuntimeError("FOOTBALL_DATA_API_KEY is not set")
    date_from = now_utc.date()
    date_to = date_from + timedelta(days=horizon_days)
    observed_at = now_utc.strftime("%Y%m%dT%H%M%SZ")
    raw_snapshot_path = raw_snapshot_root / f"{observed_at}.json"
    client = FootballDataOrgClient(api_key=api_key)
    fixtures = collect_upcoming_fixtures(
        client,
        sorted(VERIFIED_FREE_COMPETITIONS),
        date_from=date_from,
        date_to=date_to,
        raw_snapshot_path=raw_snapshot_path,
    )
    history = load_historical_matches(history_root)
    run = produce_runtime_forecasts(history, fixtures)
    write_runtime_forecasts(
        output_path,
        run.selections,
        generated_at_utc=now_utc,
    )
    return {
        "history_matches": run.history_size,
        "training_matches": run.training_size,
        "calibration_matches": run.calibration_size,
        "upcoming_fixtures": run.fixture_size,
        "qualified_selections": len(run.selections),
        "runtime_output": str(output_path),
        "raw_snapshot": str(raw_snapshot_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history-root",
        type=Path,
        default=Path("raw-data/football-data-org"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/runtime/football-report-selections.json"),
    )
    parser.add_argument(
        "--raw-snapshot-root",
        type=Path,
        default=Path("raw-data/football-data-org/upcoming"),
    )
    parser.add_argument("--horizon-days", type=int, default=7)
    args = parser.parse_args()
    result = produce(
        history_root=args.history_root,
        output_path=args.output,
        raw_snapshot_root=args.raw_snapshot_root,
        horizon_days=args.horizon_days,
        now_utc=datetime.now(UTC),
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
