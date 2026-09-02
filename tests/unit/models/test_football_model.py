from datetime import UTC, datetime, timedelta

import pytest

from sports_edge.domain.football import (
    Competition,
    FootballMatch,
    FootballScore,
    MatchStatus,
)
from sports_edge.features.football import FootballFeatureBuilder
from sports_edge.models.football import (
    FootballPoissonModel,
    FootballProbabilities,
    chronological_split,
    evaluate_probabilities,
)

COMPETITION = Competition(source_id="2021", code="PL", name="Premier League")


def historical_match(index: int) -> FootballMatch:
    teams = (("A", "B"), ("C", "D"), ("A", "C"), ("B", "D"))
    home_id, away_id = teams[index % len(teams)]
    home_goals = (index * 2) % 4
    away_goals = (index + 1) % 3
    return FootballMatch(
        source="football-data.org",
        source_id=str(index),
        competition=COMPETITION,
        kickoff_utc=datetime(2024, 1, 1, 15, tzinfo=UTC) + timedelta(days=index),
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


def snapshots(count: int = 40):
    return FootballFeatureBuilder().build(
        [historical_match(index) for index in range(count)]
    )


def test_chronological_split_has_non_overlapping_boundaries() -> None:
    features = snapshots(8)

    split = chronological_split(
        features,
        validation_start=datetime(2024, 1, 4, tzinfo=UTC),
        holdout_start=datetime(2024, 1, 7, tzinfo=UTC),
    )

    assert [item.source_id for item in split.train] == ["0", "1", "2"]
    assert [item.source_id for item in split.validation] == ["3", "4", "5"]
    assert [item.source_id for item in split.holdout] == ["6", "7"]


def test_poisson_probabilities_are_bounded_and_coherent() -> None:
    features = snapshots()
    model = FootballPoissonModel()
    model.fit(features[:30])

    probabilities = model.predict(features[30])

    assert probabilities.expected_home_goals > 0.0
    assert probabilities.expected_away_goals > 0.0
    result_probability = (
        probabilities.home_win + probabilities.draw + probabilities.away_win
    )
    assert result_probability == pytest.approx(1.0)
    assert 0.0 <= probabilities.over_2_5 <= 1.0
    assert 0.0 <= probabilities.both_teams_to_score <= 1.0
    assert model.training_cutoff == features[29].kickoff_utc


def test_multiclass_metrics_report_accuracy_brier_and_log_loss() -> None:
    probabilities = FootballProbabilities(
        expected_home_goals=1.5,
        expected_away_goals=1.0,
        home_win=0.6,
        draw=0.3,
        away_win=0.1,
        over_2_5=0.5,
        both_teams_to_score=0.5,
    )

    metrics = evaluate_probabilities([(probabilities, "HOME")])

    assert metrics.sample_size == 1
    assert metrics.accuracy == 1.0
    assert metrics.multiclass_brier == pytest.approx(0.26)
    assert metrics.log_loss == pytest.approx(0.5108256237659907)


def test_validation_only_calibration_preserves_coherent_probabilities() -> None:
    features = snapshots()
    model = FootballPoissonModel()
    model.fit(features[:30])

    model.calibrate(features[30:35])
    probabilities = model.predict(features[35])

    assert model.calibration_cutoff == features[34].kickoff_utc
    result_probability = (
        probabilities.home_win + probabilities.draw + probabilities.away_win
    )
    assert result_probability == pytest.approx(1.0)
    assert 0.0 <= probabilities.over_2_5 <= 1.0
    assert 0.0 <= probabilities.both_teams_to_score <= 1.0


def test_fit_accepts_regime_sample_weights_and_rejects_length_mismatch() -> None:
    features = snapshots()
    model = FootballPoissonModel()

    with pytest.raises(ValueError, match="sample_weights"):
        model.fit(features[:30], sample_weights=[1.0] * 29)

    model.fit(features[:30], sample_weights=[0.5] * 15 + [1.0] * 15)

    assert model.training_cutoff == features[29].kickoff_utc
