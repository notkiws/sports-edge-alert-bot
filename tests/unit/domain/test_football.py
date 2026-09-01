from datetime import UTC, datetime

import pytest

from sports_edge.domain.football import (
    Competition,
    FootballMatch,
    FootballScore,
    MatchStatus,
)


def test_canonical_match_preserves_provider_identity_and_scores() -> None:
    kickoff = datetime(2026, 9, 2, 18, 30, tzinfo=UTC)
    match = FootballMatch(
        source="football-data.org",
        source_id="54321",
        competition=Competition(source_id="2021", code="PL", name="Premier League"),
        kickoff_utc=kickoff,
        home_team_id="61",
        home_team_name="Chelsea FC",
        away_team_id="64",
        away_team_name="Liverpool FC",
        status=MatchStatus.FINISHED,
        score=FootballScore(full_time_home=2, full_time_away=1, half_time_home=1, half_time_away=0),
    )

    assert match.kickoff_utc == kickoff
    assert match.score.full_time == (2, 1)
    assert match.score.half_time == (1, 0)
    assert match.quality_flags == frozenset()


def test_canonical_match_rejects_non_utc_kickoff() -> None:
    with pytest.raises(ValueError, match="UTC"):
        FootballMatch(
            source="football-data.org",
            source_id="1",
            competition=Competition(source_id="2021", code="PL", name="Premier League"),
            kickoff_utc=datetime(2026, 9, 2, 18, 30),
            home_team_id="1",
            home_team_name="Home",
            away_team_id="2",
            away_team_name="Away",
            status=MatchStatus.SCHEDULED,
            score=FootballScore(),
        )


def test_score_does_not_invent_missing_periods() -> None:
    score = FootballScore(full_time_home=1, full_time_away=1)

    assert score.full_time == (1, 1)
    assert score.half_time is None
