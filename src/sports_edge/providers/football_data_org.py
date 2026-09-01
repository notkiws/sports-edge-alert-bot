"""football-data.org response normalization."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sports_edge.domain.football import (
    Competition,
    FootballMatch,
    FootballScore,
    MatchStatus,
)

VERIFIED_FREE_COMPETITIONS = frozenset({"PL", "PD", "SA", "DED", "CL"})


class UnsupportedCompetition(ValueError):
    """Raised when a match is outside verified free-account coverage."""


class ProviderPayloadError(ValueError):
    """Raised when required provider identity fields are absent."""


def _mapping(value: object, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderPayloadError(f"{field_name} must be an object")
    return value


def _score_value(period: Mapping[str, Any], side: str) -> int | None:
    value = period.get(side)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ProviderPayloadError(f"score {side} must be an integer or null")
    return value


class FootballDataOrgAdapter:
    """Normalize football-data.org payloads into canonical entities."""

    def __init__(
        self,
        allowed_competition_codes: frozenset[str] = VERIFIED_FREE_COMPETITIONS,
    ) -> None:
        self.allowed_competition_codes = allowed_competition_codes

    def normalize_match(self, payload: Mapping[str, Any]) -> FootballMatch:
        competition_payload = _mapping(payload.get("competition"), "competition")
        competition_code = str(competition_payload.get("code", ""))
        if competition_code not in self.allowed_competition_codes:
            raise UnsupportedCompetition(f"competition {competition_code!r} is not enabled")

        home_team = _mapping(payload.get("homeTeam"), "homeTeam")
        away_team = _mapping(payload.get("awayTeam"), "awayTeam")
        score_payload = _mapping(payload.get("score", {}), "score")
        full_time = _mapping(score_payload.get("fullTime", {}), "score.fullTime")
        half_time = _mapping(score_payload.get("halfTime", {}), "score.halfTime")

        status = MatchStatus(str(payload.get("status", "")))
        score = FootballScore(
            full_time_home=_score_value(full_time, "home"),
            full_time_away=_score_value(full_time, "away"),
            half_time_home=_score_value(half_time, "home"),
            half_time_away=_score_value(half_time, "away"),
        )
        quality_flags: set[str] = set()
        if status is MatchStatus.FINISHED:
            if score.full_time is None:
                quality_flags.add("MISSING_FULL_TIME_SCORE")
            if score.half_time is None:
                quality_flags.add("MISSING_HALF_TIME_SCORE")

        kickoff_raw = payload.get("utcDate")
        if not isinstance(kickoff_raw, str):
            raise ProviderPayloadError("utcDate must be a string")

        return FootballMatch(
            source="football-data.org",
            source_id=str(payload.get("id", "")),
            competition=Competition(
                source_id=str(competition_payload.get("id", "")),
                code=competition_code,
                name=str(competition_payload.get("name", "")),
            ),
            kickoff_utc=datetime.fromisoformat(kickoff_raw.replace("Z", "+00:00")),
            home_team_id=str(home_team.get("id", "")),
            home_team_name=str(home_team.get("name", "")),
            away_team_id=str(away_team.get("id", "")),
            away_team_name=str(away_team.get("name", "")),
            status=status,
            score=score,
            quality_flags=frozenset(quality_flags),
        )
