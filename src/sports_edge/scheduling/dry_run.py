"""Deterministic WIB daily report grouping without message delivery."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from sports_edge.config import Settings
from sports_edge.reporting.telegram import FootballReportSelection, render_daily_report


@dataclass(frozen=True, slots=True)
class DailyReportBatch:
    local_date: date
    scheduled_for_utc: datetime
    selections: tuple[FootballReportSelection, ...]


def build_daily_batches(
    selections: Iterable[FootballReportSelection],
) -> tuple[DailyReportBatch, ...]:
    """Group selections by WIB date and schedule from the earliest kickoff."""

    timezone = Settings().timezone
    grouped: dict[date, list[FootballReportSelection]] = defaultdict(list)
    for selection in selections:
        grouped[selection.kickoff_utc.astimezone(timezone).date()].append(selection)
    batches: list[DailyReportBatch] = []
    for local_date, day_selections in grouped.items():
        ordered = tuple(
            sorted(
                day_selections,
                key=lambda item: (item.kickoff_utc, item.competition, item.home_team),
            )
        )
        batches.append(
            DailyReportBatch(
                local_date=local_date,
                scheduled_for_utc=ordered[0].kickoff_utc - timedelta(hours=3),
                selections=ordered,
            )
        )
    return tuple(sorted(batches, key=lambda item: item.local_date))


def write_dry_run_batches(
    batches: Iterable[DailyReportBatch],
    destination: Path,
) -> tuple[Path, ...]:
    """Atomically materialize bilingual reports without sending them."""

    timezone = Settings().timezone
    destination.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for batch in batches:
        path = destination / f"{batch.local_date.isoformat()}.txt"
        temporary = path.with_suffix(".txt.tmp")
        scheduled_wib = batch.scheduled_for_utc.astimezone(timezone)
        content = "\n".join(
            (
                "DRY RUN — NOT SENT",
                "UJI COBA — TIDAK DIKIRIM",
                (
                    "Scheduled / Dijadwalkan: "
                    f"{scheduled_wib.strftime('%d %b %Y, %H:%M WIB')}"
                ),
                "",
                render_daily_report(batch.selections),
                "",
            )
        )
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
        written.append(path)
    return tuple(written)


def write_due_dry_run_batches(
    batches: Iterable[DailyReportBatch],
    *,
    now_utc: datetime,
    destination: Path,
    polling_window: timedelta = timedelta(minutes=15),
) -> tuple[Path, ...]:
    """Write only due reports, preserving the first artifact for each WIB day."""

    due = tuple(
        batch
        for batch in batches
        if batch.scheduled_for_utc <= now_utc < batch.scheduled_for_utc + polling_window
        and not (destination / f"{batch.local_date.isoformat()}.txt").exists()
    )
    return write_dry_run_batches(due, destination)
