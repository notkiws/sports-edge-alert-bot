import json
from datetime import UTC, datetime
from pathlib import Path

from sports_edge.commands.render_telegram_dry_run import render_dry_run, render_due_dry_run


def test_render_dry_run_command_reads_forecasts_and_writes_report(tmp_path: Path) -> None:
    source = tmp_path / "forecasts.json"
    source.write_text(
        json.dumps(
            {
                "football": [
                    {
                        "competition": "Premier League",
                        "kickoff_utc": "2026-09-03T15:00:00Z",
                        "home_team": "Arsenal",
                        "away_team": "Chelsea",
                        "market": "1X2",
                        "selection_en": "HOME",
                        "selection_id": "TUAN RUMAH",
                        "probability": 0.68,
                        "historical_hit_rate": 0.70,
                        "historical_sample_size": 120,
                        "grade": "A",
                        "reasoning_en": "Calibrated probability qualifies.",
                        "reasoning_id": "Probabilitas terkalibrasi memenuhi syarat.",
                        "warning_en": "Odds were not evaluated.",
                        "warning_id": "Odds tidak dievaluasi.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    paths = render_dry_run(source, tmp_path / "reports")

    assert paths == (tmp_path / "reports" / "2026-09-03.txt",)
    assert "DRY RUN — NOT SENT" in paths[0].read_text()


def test_render_due_dry_run_writes_only_inside_schedule_window(tmp_path: Path) -> None:
    source = tmp_path / "forecasts.json"
    source.write_text(
        json.dumps(
            {
                "football": [
                    {
                        "competition": "Premier League",
                        "kickoff_utc": "2026-09-03T15:00:00Z",
                        "home_team": "Arsenal",
                        "away_team": "Chelsea",
                        "market": "1X2",
                        "selection_en": "HOME",
                        "selection_id": "TUAN RUMAH",
                        "probability": 0.68,
                        "historical_hit_rate": 0.70,
                        "historical_sample_size": 120,
                        "grade": "A",
                        "reasoning_en": "Reason.",
                        "reasoning_id": "Alasan.",
                        "warning_en": "Warning.",
                        "warning_id": "Peringatan.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert not render_due_dry_run(
        source,
        tmp_path / "reports",
        now_utc=datetime(2026, 9, 3, 11, 59, tzinfo=UTC),
    )
    assert render_due_dry_run(
        source,
        tmp_path / "reports",
        now_utc=datetime(2026, 9, 3, 12, 1, tzinfo=UTC),
    )
