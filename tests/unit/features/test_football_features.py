from datetime import UTC, datetime

from sports_edge.domain.football import (
    Competition,
    FootballMatch,
    FootballScore,
    MatchStatus,
)
from sports_edge.features.football import FootballFeatureBuilder

COMPETITION = Competition(source_id="2021", code="PL", name="Premier League")


def match(
    *,
    day: int,
    home_id: str,
    away_id: str,
    home_goals: int,
    away_goals: int,
    source_id: str,
) -> FootballMatch:
    return FootballMatch(
        source="football-data.org",
        source_id=source_id,
        competition=COMPETITION,
        kickoff_utc=datetime(2025, 1, day, 15, tzinfo=UTC),
        home_team_id=home_id,
        home_team_name=f"Team {home_id}",
        away_team_id=away_id,
        away_team_name=f"Team {away_id}",
        status=MatchStatus.FINISHED,
        score=FootballScore(
            full_time_home=home_goals,
            full_time_away=away_goals,
            half_time_home=0,
            half_time_away=0,
        ),
    )


def test_first_fixture_has_neutral_point_in_time_features() -> None:
    historical_match = match(
        day=1,
        home_id="A",
        away_id="B",
        home_goals=2,
        away_goals=0,
        source_id="1",
    )

    snapshot = FootballFeatureBuilder().build([historical_match])[0]

    assert snapshot.home_team_id == "A"
    assert snapshot.away_team_id == "B"
    assert snapshot.home_prior_matches == 0
    assert snapshot.away_prior_matches == 0
    assert snapshot.home_last_10_goals_for is None
    assert snapshot.away_last_10_goals_for is None
    assert snapshot.prior_h2h_matches == 0
    assert snapshot.full_time_home_goals == 2
    assert snapshot.full_time_away_goals == 0


def test_later_fixture_uses_only_prior_results() -> None:
    matches = [
        match(
            day=1,
            home_id="A",
            away_id="B",
            home_goals=2,
            away_goals=0,
            source_id="1",
        ),
        match(
            day=2,
            home_id="B",
            away_id="A",
            home_goals=1,
            away_goals=1,
            source_id="2",
        ),
    ]

    snapshot = FootballFeatureBuilder().build(matches)[1]

    assert snapshot.home_prior_matches == 1
    assert snapshot.away_prior_matches == 1
    assert snapshot.home_last_10_goals_for == 0.0
    assert snapshot.home_last_10_goals_against == 2.0
    assert snapshot.home_last_10_points_per_match == 0.0
    assert snapshot.away_last_10_goals_for == 2.0
    assert snapshot.away_last_10_goals_against == 0.0
    assert snapshot.away_last_10_points_per_match == 3.0
    assert snapshot.home_days_rest == 1
    assert snapshot.away_days_rest == 1
    assert snapshot.prior_h2h_matches == 1


def test_same_date_fixtures_cannot_see_each_others_results() -> None:
    matches = [
        match(
            day=1,
            home_id="A",
            away_id="B",
            home_goals=2,
            away_goals=0,
            source_id="1",
        ),
        match(
            day=1,
            home_id="B",
            away_id="A",
            home_goals=1,
            away_goals=1,
            source_id="2",
        ),
    ]

    second_snapshot = FootballFeatureBuilder().build(matches)[1]

    assert second_snapshot.home_prior_matches == 0
    assert second_snapshot.away_prior_matches == 0
    assert second_snapshot.home_last_10_goals_for is None
    assert second_snapshot.away_last_10_goals_for is None
    assert second_snapshot.prior_h2h_matches == 0


def test_upcoming_fixture_uses_prior_results_without_score_target() -> None:
    historical_match = match(
        day=1,
        home_id="A",
        away_id="B",
        home_goals=2,
        away_goals=0,
        source_id="1",
    )
    upcoming = FootballMatch(
        source="football-data.org",
        source_id="2",
        competition=COMPETITION,
        kickoff_utc=datetime(2025, 1, 2, 15, tzinfo=UTC),
        home_team_id="B",
        home_team_name="Team B",
        away_team_id="A",
        away_team_name="Team A",
        status=MatchStatus.SCHEDULED,
        score=FootballScore(),
    )

    snapshot = FootballFeatureBuilder().build_upcoming(
        (historical_match,),
        (upcoming,),
    )[0]

    assert snapshot.source_id == "2"
    assert snapshot.home_team_name == "Team B"
    assert snapshot.away_team_name == "Team A"
    assert snapshot.home_prior_matches == 1
    assert snapshot.away_prior_matches == 1
    assert snapshot.home_last_10_goals_for == 0.0
    assert snapshot.away_last_10_goals_for == 2.0
    assert not hasattr(snapshot, "full_time_home_goals")
