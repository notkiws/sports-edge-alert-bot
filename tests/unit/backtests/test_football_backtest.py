from dataclasses import replace
from datetime import timedelta

import pytest

from sports_edge.backtests.football import (
    qualify_forecasts,
    run_football_fold,
    summarize_forecasts,
)
from sports_edge.features.football import FootballFeatureSnapshot
from sports_edge.models.football import FootballProbabilities


def snapshot() -> FootballFeatureSnapshot:
    from datetime import UTC, datetime

    return FootballFeatureSnapshot(
        source_id="1",
        competition_code="PL",
        kickoff_utc=datetime(2025, 1, 1, tzinfo=UTC),
        home_team_id="A",
        away_team_id="B",
        home_prior_matches=10,
        away_prior_matches=10,
        home_last_10_goals_for=1.5,
        home_last_10_goals_against=1.0,
        home_last_10_points_per_match=2.0,
        away_last_10_goals_for=1.0,
        away_last_10_goals_against=1.5,
        away_last_10_points_per_match=1.0,
        home_days_rest=7,
        away_days_rest=7,
        prior_h2h_matches=3,
        full_time_home_goals=2,
        full_time_away_goals=1,
    )


def test_qualification_requires_floor_and_returns_at_most_three_ranked_options() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.8,
        expected_away_goals=0.9,
        home_win=0.62,
        draw=0.23,
        away_win=0.15,
        over_2_5=0.70,
        both_teams_to_score=0.65,
    )

    forecasts = qualify_forecasts(
        snapshot(),
        probabilities,
        probability_floor=0.60,
        enabled_markets=("1X2", "TOTAL_2_5", "BTTS"),
    )

    assert [(item.market, item.selection) for item in forecasts] == [
        ("TOTAL_2_5", "OVER"),
        ("BTTS", "YES"),
        ("1X2", "HOME"),
    ]
    assert all(item.probability >= 0.60 for item in forecasts)
    assert all(item.correct for item in forecasts)


def test_qualification_abstains_when_every_option_is_below_floor() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.2,
        expected_away_goals=1.1,
        home_win=0.40,
        draw=0.31,
        away_win=0.29,
        over_2_5=0.55,
        both_teams_to_score=0.52,
    )

    assert qualify_forecasts(snapshot(), probabilities, probability_floor=0.60) == ()


def test_default_policy_excludes_disabled_btts_market() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.2,
        expected_away_goals=1.1,
        home_win=0.40,
        draw=0.31,
        away_win=0.29,
        over_2_5=0.55,
        both_teams_to_score=0.75,
    )

    forecasts = qualify_forecasts(snapshot(), probabilities, probability_floor=0.60)

    assert all(item.market != "BTTS" for item in forecasts)


def test_summary_reports_uncertainty_and_calibration_metrics() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.0,
        expected_away_goals=1.0,
        home_win=0.8,
        draw=0.1,
        away_win=0.1,
        over_2_5=0.8,
        both_teams_to_score=0.8,
    )
    winning = qualify_forecasts(snapshot(), probabilities, probability_floor=0.60)
    losing_snapshot = replace(
        snapshot(),
        full_time_home_goals=0,
        full_time_away_goals=1,
    )
    losing = qualify_forecasts(losing_snapshot, probabilities, probability_floor=0.60)

    metrics = summarize_forecasts((winning[0], losing[0]))

    assert metrics.sample_size == 2
    assert metrics.hit_rate == 0.5
    assert metrics.brier_score == pytest.approx(0.34)
    assert metrics.expected_calibration_error == pytest.approx(0.3)
    assert metrics.wilson_low < metrics.hit_rate < metrics.wilson_high


def test_fold_trains_calibrates_and_evaluates_non_overlapping_periods() -> None:
    baseline = snapshot()
    features = tuple(
        replace(
            baseline,
            source_id=str(index),
            kickoff_utc=baseline.kickoff_utc + timedelta(days=index),
            full_time_home_goals=(index * 2) % 4,
            full_time_away_goals=(index + 1) % 3,
        )
        for index in range(40)
    )

    fold = run_football_fold(
        features,
        calibration_start=baseline.kickoff_utc + timedelta(days=30),
        evaluation_start=baseline.kickoff_utc + timedelta(days=35),
        evaluation_end=baseline.kickoff_utc + timedelta(days=40),
        probability_floor=0.50,
    )

    assert fold.train_size == 30
    assert fold.calibration_size == 5
    assert fold.evaluation_size == 5
    assert fold.forecasts
    assert {item.source_id for item in fold.forecasts} <= {
        "35",
        "36",
        "37",
        "38",
        "39",
    }
