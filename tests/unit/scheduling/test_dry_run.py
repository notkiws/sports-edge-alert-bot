from datetime import UTC, date, datetime

from sports_edge.reporting.telegram import FootballReportSelection
from sports_edge.scheduling.dry_run import (
    build_daily_batches,
    write_dry_run_batches,
    write_due_dry_run_batches,
)


def report_selection(kickoff_utc: datetime, home: str) -> FootballReportSelection:
    return FootballReportSelection(
        competition="Premier League",
        kickoff_utc=kickoff_utc,
        home_team=home,
        away_team="Away",
        market="1X2",
        selection_en="HOME",
        selection_id="TUAN RUMAH",
        probability=0.68,
        historical_hit_rate=0.70,
        historical_sample_size=120,
        grade="A",
        reasoning_en="Reason.",
        reasoning_id="Alasan.",
        warning_en="Uncertain.",
        warning_id="Tidak pasti.",
    )


def test_daily_batches_group_by_wib_and_schedule_three_hours_before_earliest() -> None:
    selections = (
        report_selection(datetime(2026, 9, 3, 15, tzinfo=UTC), "First"),
        report_selection(datetime(2026, 9, 3, 16, tzinfo=UTC), "Later"),
        report_selection(datetime(2026, 9, 4, 18, tzinfo=UTC), "Next day"),
    )

    batches = build_daily_batches(selections)

    assert len(batches) == 2
    assert batches[0].local_date == date(2026, 9, 3)
    assert batches[0].scheduled_for_utc == datetime(2026, 9, 3, 12, tzinfo=UTC)
    assert [item.home_team for item in batches[0].selections] == ["First", "Later"]
    assert batches[1].local_date == date(2026, 9, 5)
    assert batches[1].scheduled_for_utc == datetime(2026, 9, 4, 15, tzinfo=UTC)


def test_write_dry_run_batches_creates_unsent_bilingual_report(tmp_path) -> None:
    batches = build_daily_batches(
        (report_selection(datetime(2026, 9, 3, 15, tzinfo=UTC), "First"),)
    )

    paths = write_dry_run_batches(batches, tmp_path)

    assert paths == (tmp_path / "2026-09-03.txt",)
    content = paths[0].read_text()
    assert content.startswith("DRY RUN — NOT SENT\nUJI COBA — TIDAK DIKIRIM\n")
    assert "Scheduled / Dijadwalkan: 03 Sep 2026, 19:00 WIB" in content
    assert "First vs Away" in content


def test_due_scheduler_waits_for_window_and_never_overwrites(tmp_path) -> None:
    batches = build_daily_batches(
        (report_selection(datetime(2026, 9, 3, 15, tzinfo=UTC), "First"),)
    )

    assert not write_due_dry_run_batches(
        batches,
        now_utc=datetime(2026, 9, 3, 11, 59, tzinfo=UTC),
        destination=tmp_path,
    )
    assert write_due_dry_run_batches(
        batches,
        now_utc=datetime(2026, 9, 3, 12, 5, tzinfo=UTC),
        destination=tmp_path,
    ) == (tmp_path / "2026-09-03.txt",)
    original = (tmp_path / "2026-09-03.txt").read_text()
    assert not write_due_dry_run_batches(
        batches,
        now_utc=datetime(2026, 9, 3, 12, 10, tzinfo=UTC),
        destination=tmp_path,
    )
    assert (tmp_path / "2026-09-03.txt").read_text() == original
