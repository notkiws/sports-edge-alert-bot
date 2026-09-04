"""Plain-text bilingual Telegram report rendering."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sports_edge.config import Settings


@dataclass(frozen=True, slots=True)
class FootballReportSelection:
    competition: str
    kickoff_utc: datetime
    home_team: str
    away_team: str
    market: str
    selection_en: str
    selection_id: str
    probability: float
    historical_hit_rate: float
    historical_sample_size: int
    grade: str
    reasoning_en: str
    reasoning_id: str
    warning_en: str
    warning_id: str


def _render_football(selection: FootballReportSelection) -> str:
    kickoff_wib = selection.kickoff_utc.astimezone(Settings().timezone)
    return "\n".join(
        (
            "⚽ FOOTBALL / SEPAK BOLA",
            "",
            selection.competition,
            kickoff_wib.strftime("%d %b %Y, %H:%M WIB"),
            f"{selection.home_team} vs {selection.away_team}",
            f"{selection.market}: {selection.selection_en} / {selection.selection_id}",
            f"Probability / Probabilitas: {selection.probability:.1%}",
            (
                "Historical / Historis: "
                f"{selection.historical_hit_rate:.1%} "
                f"(n={selection.historical_sample_size})"
            ),
            f"Grade / Nilai: {selection.grade}",
        )
    )


def render_daily_report(selections: Iterable[FootballReportSelection]) -> str:
    """Render chronological football selections as plain Telegram-safe text."""

    settings = Settings()
    ordered = sorted(
        (
            selection
            for selection in selections
            if selection.market in settings.football_enabled_markets
            and selection.probability >= settings.football_probability_floor
        ),
        key=lambda item: (item.kickoff_utc, item.competition, item.home_team),
    )
    if not ordered:
        return (
            "No qualifying selections today.\n"
            "Tidak ada pilihan yang memenuhi syarat hari ini."
        )
    return "\n\n".join(_render_football(selection) for selection in ordered)
