"""Render scheduled bilingual Telegram reports without sending them."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sports_edge.reporting.telegram import FootballReportSelection
from sports_edge.scheduling.dry_run import (
    build_daily_batches,
    write_dry_run_batches,
    write_due_dry_run_batches,
)


def _datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("kickoff_utc must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("kickoff_utc must be timezone-aware")
    return parsed


def _selection(value: object) -> FootballReportSelection:
    if not isinstance(value, dict):
        raise ValueError("each football forecast must be an object")
    return FootballReportSelection(
        competition=str(value["competition"]),
        kickoff_utc=_datetime(value["kickoff_utc"]),
        home_team=str(value["home_team"]),
        away_team=str(value["away_team"]),
        market=str(value["market"]),
        selection_en=str(value["selection_en"]),
        selection_id=str(value["selection_id"]),
        probability=float(value["probability"]),
        historical_hit_rate=float(value["historical_hit_rate"]),
        historical_sample_size=int(value["historical_sample_size"]),
        grade=str(value["grade"]),
        reasoning_en=str(value["reasoning_en"]),
        reasoning_id=str(value["reasoning_id"]),
        warning_en=str(value["warning_en"]),
        warning_id=str(value["warning_id"]),
    )


def _load_selections(source: Path) -> tuple[FootballReportSelection, ...]:
    payload: object = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("football"), list):
        raise ValueError("input must contain a football list")
    return tuple(_selection(value) for value in payload["football"])


def render_dry_run(source: Path, destination: Path) -> tuple[Path, ...]:
    """Load structured forecasts and materialize unsent daily reports."""

    return write_dry_run_batches(
        build_daily_batches(_load_selections(source)),
        destination,
    )


def render_due_dry_run(
    source: Path,
    destination: Path,
    *,
    now_utc: datetime,
) -> tuple[Path, ...]:
    """Materialize only reports currently due in the polling window."""

    return write_due_dry_run_batches(
        build_daily_batches(_load_selections(source)),
        now_utc=now_utc,
        destination=destination,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render reports without Telegram delivery.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("artifacts/telegram-dry-run"),
    )
    parser.add_argument("--due-only", action="store_true")
    arguments = parser.parse_args()
    paths = (
        render_due_dry_run(
            arguments.input,
            arguments.destination,
            now_utc=datetime.now(UTC),
        )
        if arguments.due_only
        else render_dry_run(arguments.input, arguments.destination)
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
