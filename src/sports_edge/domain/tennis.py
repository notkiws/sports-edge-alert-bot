"""Canonical tennis entities."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class TennisTour(StrEnum):
    ATP = "ATP"
    WTA = "WTA"


class TournamentLevel(StrEnum):
    LEVEL_500 = "500"
    LEVEL_1000 = "1000"
    FINALS = "FINALS"
    GRAND_SLAM = "GRAND_SLAM"


class TennisMatchStatus(StrEnum):
    COMPLETED = "Completed"
    RETIRED = "Retired"
    WALKOVER = "Walkover"
    AWARDED = "Awarded"


@dataclass(frozen=True, slots=True)
class HistoricalTennisMatch:
    source: str
    source_file: str
    source_row: int
    tour: TennisTour
    tournament: str
    location: str
    played_on: date
    level: TournamentLevel
    court: str
    surface: str
    round_name: str
    winner: str
    loser: str
    winner_rank: int | None
    loser_rank: int | None
    status: TennisMatchStatus
