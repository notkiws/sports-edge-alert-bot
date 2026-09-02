from datetime import date

import pytest

from sports_edge.domain.tennis import (
    HistoricalTennisMatch,
    TennisMatchStatus,
    TennisTour,
    TournamentLevel,
)
from sports_edge.features.tennis import TennisFeatureBuilder
from sports_edge.models.tennis import (
    TennisLogisticModel,
    chronological_split,
    evaluate_probabilities,
)


def historical_match(played_on: date, source_row: int) -> HistoricalTennisMatch:
    return HistoricalTennisMatch(
        source="tennis-data.co.uk",
        source_file="test.xlsx",
        source_row=source_row,
        tour=TennisTour.ATP,
        tournament="Example Open",
        location="London",
        played_on=played_on,
        level=TournamentLevel.LEVEL_500,
        court="Outdoor",
        surface="Hard",
        round_name="1st Round",
        winner="Alpha A." if source_row % 2 == 0 else "Beta B.",
        loser="Beta B." if source_row % 2 == 0 else "Alpha A.",
        winner_rank=10,
        loser_rank=20,
        status=TennisMatchStatus.COMPLETED,
    )


def test_chronological_split_has_non_overlapping_date_boundaries() -> None:
    snapshots = TennisFeatureBuilder().build(
        [
            historical_match(date(2025, 1, 5), 6),
            historical_match(date(2025, 1, 1), 2),
            historical_match(date(2025, 1, 3), 4),
        ]
    )

    split = chronological_split(
        snapshots,
        validation_start=date(2025, 1, 3),
        holdout_start=date(2025, 1, 5),
    )

    assert [item.played_on for item in split.train] == [date(2025, 1, 1)]
    assert [item.played_on for item in split.validation] == [date(2025, 1, 3)]
    assert [item.played_on for item in split.holdout] == [date(2025, 1, 5)]


def test_logistic_model_records_training_cutoff_and_returns_probability() -> None:
    snapshots = TennisFeatureBuilder().build(
        [historical_match(date(2025, 1, day), day) for day in range(1, 21)]
    )
    model = TennisLogisticModel()

    model.fit(snapshots[:16])
    probability = model.predict_player_a_probability(snapshots[16])

    assert model.training_cutoff == date(2025, 1, 16)
    assert 0.0 <= probability <= 1.0


def test_probability_metrics_report_hit_rate_brier_and_log_loss() -> None:
    metrics = evaluate_probabilities([(0.8, True), (0.2, False)])

    assert metrics.sample_size == 2
    assert metrics.hit_rate == 1.0
    assert metrics.brier_score == pytest.approx(0.04)
    assert metrics.log_loss == pytest.approx(0.223143551314210)


def test_platt_calibration_uses_only_later_validation_snapshots() -> None:
    snapshots = TennisFeatureBuilder().build(
        [historical_match(date(2025, 1, day), day) for day in range(1, 21)]
    )
    model = TennisLogisticModel()
    model.fit(snapshots[:12])

    model.calibrate(snapshots[12:16])
    probability = model.predict_player_a_probability(snapshots[16])

    assert model.calibration_cutoff == date(2025, 1, 16)
    assert 0.0 <= probability <= 1.0
