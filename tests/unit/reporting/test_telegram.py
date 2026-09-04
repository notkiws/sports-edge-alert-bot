from dataclasses import replace
from datetime import UTC, datetime

from sports_edge.reporting.telegram import FootballReportSelection, render_daily_report


def selection() -> FootballReportSelection:
    return FootballReportSelection(
        competition="Premier League",
        kickoff_utc=datetime(2026, 9, 3, 15, tzinfo=UTC),
        home_team="Arsenal",
        away_team="Chelsea",
        market="1X2",
        selection_en="HOME",
        selection_id="TUAN RUMAH",
        probability=0.68,
        historical_hit_rate=0.70,
        historical_sample_size=120,
        grade="A",
        reasoning_en="Strong calibrated home-result probability.",
        reasoning_id="Probabilitas hasil kandang terkalibrasi kuat.",
        warning_en="Forecast uncertainty remains.",
        warning_id="Ketidakpastian prediksi tetap ada.",
    )


def test_render_football_selection_uses_concise_bilingual_format() -> None:
    message = render_daily_report((selection(),))

    assert message == (
        "⚽ FOOTBALL / SEPAK BOLA\n"
        "\n"
        "Premier League\n"
        "03 Sep 2026, 22:00 WIB\n"
        "Arsenal vs Chelsea\n"
        "1X2: HOME / TUAN RUMAH\n"
        "Probability / Probabilitas: 68.0%\n"
        "Historical / Historis: 70.0% (n=120)\n"
        "Grade / Nilai: A"
    )
    assert "ODDS NOT EVALUATED" not in message
    assert "EN:" not in message
    assert "Warning / Peringatan:" not in message


def test_render_empty_day_is_bilingual() -> None:
    assert render_daily_report(()) == (
        "No qualifying selections today.\n"
        "Tidak ada pilihan yang memenuhi syarat hari ini."
    )


def test_render_filters_below_floor_and_disabled_markets() -> None:
    message = render_daily_report(
        (
            replace(selection(), probability=0.59),
            replace(selection(), market="BTTS", probability=0.80),
        )
    )

    assert message == (
        "No qualifying selections today.\n"
        "Tidak ada pilihan yang memenuhi syarat hari ini."
    )
