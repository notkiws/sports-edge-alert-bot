"""Canonical football entities used by provider adapters and models."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum


class MatchStatus(StrEnum):
    """Provider-independent football match status."""

    SCHEDULED = "SCHEDULED"
    TIMED = "TIMED"
    IN_PLAY = "IN_PLAY"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    SUSPENDED = "SUSPENDED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    AWARDED = "AWARDED"


@dataclass(frozen=True, slots=True)
class Competition:
    """A competition with stable provider identity."""

    source_id: str
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class FootballScore:
    """Canonical full-time and half-time score values."""

    full_time_home: int | None = None
    full_time_away: int | None = None
    half_time_home: int | None = None
    half_time_away: int | None = None

    @property
    def full_time(self) -> tuple[int, int] | None:
        if self.full_time_home is None or self.full_time_away is None:
            return None
        return (self.full_time_home, self.full_time_away)

    @property
    def half_time(self) -> tuple[int, int] | None:
        if self.half_time_home is None or self.half_time_away is None:
            return None
        return (self.half_time_home, self.half_time_away)


@dataclass(frozen=True, slots=True)
class FootballMatch:
    """A normalized football fixture or result."""

    source: str
    source_id: str
    competition: Competition
    kickoff_utc: datetime
    home_team_id: str
    home_team_name: str
    away_team_id: str
    away_team_name: str
    status: MatchStatus
    score: FootballScore
    quality_flags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.kickoff_utc.tzinfo is None or self.kickoff_utc.utcoffset() != timedelta(0):
            raise ValueError("kickoff_utc must be timezone-aware UTC")
