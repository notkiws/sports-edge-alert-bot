import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sports_edge.domain.football import (
    Competition,
    FootballMatch,
    FootballScore,
    MatchStatus,
)
from sports_edge.features.football import UpcomingFootballFeatureSnapshot
from sports_edge.models.football import FootballProbabilities
from sports_edge.runtime.football import (
    collect_upcoming_fixtures,
    load_historical_matches,
    produce_runtime_forecasts,
    qualify_runtime_forecasts,
    write_runtime_forecasts,
)


class FakeFixtureClient:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = payload
        self.calls = []

    def fetch_competition_matches_between(self, competition_code, date_from, date_to):
        self.calls.append((competition_code, date_from, date_to))
        return self.payload


def snapshot() -> UpcomingFootballFeatureSnapshot:
    return UpcomingFootballFeatureSnapshot(
        source_id="fixture-1",
        competition_code="PL",
        competition_name="Premier League",
        kickoff_utc=datetime(2026, 9, 3, 15, tzinfo=UTC),
        home_team_id="A",
        home_team_name="Arsenal",
        away_team_id="B",
        away_team_name="Chelsea",
        home_prior_matches=20,
        away_prior_matches=20,
        home_last_10_goals_for=2.0,
        home_last_10_goals_against=0.8,
        home_last_10_points_per_match=2.2,
        away_last_10_goals_for=1.1,
        away_last_10_goals_against=1.5,
        away_last_10_points_per_match=1.2,
        home_days_rest=7,
        away_days_rest=7,
        prior_h2h_matches=4,
    )


def test_runtime_qualification_uses_only_frozen_markets_and_metrics() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.8,
        expected_away_goals=0.8,
        home_win=0.65,
        draw=0.22,
        away_win=0.13,
        over_2_5=0.70,
        both_teams_to_score=0.90,
    )

    selections = qualify_runtime_forecasts(snapshot(), probabilities)

    assert [(item.market, item.selection_en) for item in selections] == [
        ("TOTAL_2_5", "OVER 2.5"),
        ("1X2", "HOME"),
    ]
    assert selections[0].historical_hit_rate == 0.6735
    assert selections[0].historical_sample_size == 294
    assert selections[1].historical_hit_rate == 0.7128
    assert selections[1].historical_sample_size == 296
    assert all(item.grade == "A" for item in selections)


def test_grade_c_reason_identifies_each_teams_prior_match_count() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.8,
        expected_away_goals=0.8,
        home_win=0.65,
        draw=0.22,
        away_win=0.13,
        over_2_5=0.70,
        both_teams_to_score=0.90,
    )

    selections = qualify_runtime_forecasts(
        replace(snapshot(), away_prior_matches=0),
        probabilities,
    )

    assert all(item.grade == "C" for item in selections)
    assert all(
        item.reasoning_en == "Limited prior-match history (Arsenal: 20, Chelsea: 0)."
        for item in selections
    )
    assert all(
        item.reasoning_id
        == "Riwayat pertandingan sebelumnya terbatas (Arsenal: 20, Chelsea: 0)."
        for item in selections
    )


def test_load_historical_matches_normalizes_private_cache(tmp_path: Path) -> None:
    season = tmp_path / "2025"
    season.mkdir()
    season.joinpath("PL.json").write_text(
        json.dumps(
            {
                "matches": [
                    {
                        "id": 1,
                        "utcDate": "2025-08-01T15:00:00Z",
                        "status": "FINISHED",
                        "competition": {
                            "id": 2021,
                            "code": "PL",
                            "name": "Premier League",
                        },
                        "homeTeam": {"id": 10, "name": "Home"},
                        "awayTeam": {"id": 20, "name": "Away"},
                        "score": {
                            "fullTime": {"home": 2, "away": 1},
                            "halfTime": {"home": 1, "away": 0},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    matches = load_historical_matches(tmp_path)

    assert len(matches) == 1
    assert matches[0].source_id == "1"
    assert matches[0].score.full_time == (2, 1)


def test_write_runtime_forecasts_is_atomic_and_scheduler_compatible(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "football-report-selections.json"
    probabilities = FootballProbabilities(
        expected_home_goals=1.8,
        expected_away_goals=0.8,
        home_win=0.65,
        draw=0.22,
        away_win=0.13,
        over_2_5=0.70,
        both_teams_to_score=0.90,
    )

    write_runtime_forecasts(
        destination,
        qualify_runtime_forecasts(snapshot(), probabilities),
        generated_at_utc=datetime(2026, 9, 2, 8, tzinfo=UTC),
    )

    payload = json.loads(destination.read_text())
    assert payload["generated_at_utc"] == "2026-09-02T08:00:00+00:00"
    assert payload["model"] == "football-poisson-v1"
    assert len(payload["football"]) == 2
    assert payload["football"][0]["kickoff_utc"] == "2026-09-03T15:00:00+00:00"
    assert not destination.with_suffix(".json.tmp").exists()


def test_produce_runtime_forecasts_fits_only_results_then_predicts_fixture() -> None:
    competition = Competition(source_id="2021", code="PL", name="Premier League")
    history = []
    outcomes = ((3, 0), (1, 1), (0, 2))
    for index in range(60):
        home_goals, away_goals = outcomes[index % len(outcomes)]
        history.append(
            FootballMatch(
                source="football-data.org",
                source_id=str(index),
                competition=competition,
                kickoff_utc=datetime(2025, 1, 1, 15, tzinfo=UTC)
                + timedelta(days=index),
                home_team_id="A" if index % 2 == 0 else "B",
                home_team_name="Team A" if index % 2 == 0 else "Team B",
                away_team_id="B" if index % 2 == 0 else "A",
                away_team_name="Team B" if index % 2 == 0 else "Team A",
                status=MatchStatus.FINISHED,
                score=FootballScore(
                    full_time_home=home_goals,
                    full_time_away=away_goals,
                    half_time_home=0,
                    half_time_away=0,
                ),
            )
        )
    fixture = FootballMatch(
        source="football-data.org",
        source_id="future",
        competition=competition,
        kickoff_utc=datetime(2025, 3, 15, 15, tzinfo=UTC),
        home_team_id="A",
        home_team_name="Team A",
        away_team_id="B",
        away_team_name="Team B",
        status=MatchStatus.TIMED,
        score=FootballScore(),
    )

    run = produce_runtime_forecasts(history, (fixture,))

    assert run.history_size == 60
    assert run.training_size > run.calibration_size > 0
    assert run.fixture_size == 1
    assert all(item.home_team == "Team A" for item in run.selections)
    assert all(item.probability >= 0.60 for item in run.selections)


def test_collect_upcoming_fixtures_normalizes_and_caches_provider_snapshot(
    tmp_path: Path,
) -> None:
    client = FakeFixtureClient(
        {
            "matches": [
                {
                    "id": 99,
                    "utcDate": "2026-09-03T15:00:00Z",
                    "status": "TIMED",
                    "competition": {
                        "id": 2021,
                        "code": "PL",
                        "name": "Premier League",
                    },
                    "homeTeam": {"id": 10, "name": "Home"},
                    "awayTeam": {"id": 20, "name": "Away"},
                    "score": {
                        "fullTime": {"home": None, "away": None},
                        "halfTime": {"home": None, "away": None},
                    },
                }
            ]
        }
    )

    fixtures = collect_upcoming_fixtures(
        client,
        ("PL",),
        date_from=datetime(2026, 9, 2, tzinfo=UTC).date(),
        date_to=datetime(2026, 9, 9, tzinfo=UTC).date(),
        raw_snapshot_path=tmp_path / "upcoming.json",
    )

    assert len(fixtures) == 1
    assert fixtures[0].source_id == "99"
    assert fixtures[0].status is MatchStatus.TIMED
    assert client.calls[0][0] == "PL"
    cached = json.loads((tmp_path / "upcoming.json").read_text())
    assert cached["competitions"]["PL"]["matches"][0]["id"] == 99


def test_collect_upcoming_fixtures_skips_malformed_irrelevant_status(
    tmp_path: Path,
) -> None:
    client = FakeFixtureClient(
        {
            "matches": [
                {
                    "id": 100,
                    "utcDate": "2026-09-04T18:00:00Z",
                    "status": "2026-09-04 18:00:00Z",
                    "competition": {
                        "id": 2021,
                        "code": "PL",
                        "name": "Premier League",
                    },
                    "homeTeam": {"id": 10, "name": "Home"},
                    "awayTeam": {"id": 20, "name": "Away"},
                    "score": {},
                }
            ]
        }
    )

    fixtures = collect_upcoming_fixtures(
        client,
        ("PL",),
        date_from=datetime(2026, 9, 2, tzinfo=UTC).date(),
        date_to=datetime(2026, 9, 9, tzinfo=UTC).date(),
        raw_snapshot_path=tmp_path / "upcoming.json",
    )

    assert fixtures == ()
