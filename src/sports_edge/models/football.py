"""Chronological football goal-distribution model."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import exp, log

from sklearn.linear_model import (  # type: ignore[import-untyped]
    LogisticRegression,
    PoissonRegressor,
)
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from sports_edge.features.football import (
    FootballFeatureSnapshot,
    UpcomingFootballFeatureSnapshot,
)

FootballPredictionSnapshot = FootballFeatureSnapshot | UpcomingFootballFeatureSnapshot


@dataclass(frozen=True, slots=True)
class ChronologicalFootballSplit:
    train: tuple[FootballFeatureSnapshot, ...]
    validation: tuple[FootballFeatureSnapshot, ...]
    holdout: tuple[FootballFeatureSnapshot, ...]


@dataclass(frozen=True, slots=True)
class FootballProbabilities:
    expected_home_goals: float
    expected_away_goals: float
    home_win: float
    draw: float
    away_win: float
    over_2_5: float
    both_teams_to_score: float


@dataclass(frozen=True, slots=True)
class FootballProbabilityMetrics:
    sample_size: int
    accuracy: float
    multiclass_brier: float
    log_loss: float


def evaluate_probabilities(
    predictions: Iterable[tuple[FootballProbabilities, str]],
) -> FootballProbabilityMetrics:
    """Evaluate 1X2 probabilities against HOME, DRAW, or AWAY outcomes."""

    rows = tuple(predictions)
    if not rows:
        raise ValueError("predictions cannot be empty")
    labels = ("HOME", "DRAW", "AWAY")
    correct = 0
    brier_total = 0.0
    log_loss_total = 0.0
    epsilon = 1e-15
    for probabilities, outcome in rows:
        if outcome not in labels:
            raise ValueError(f"unsupported outcome {outcome!r}")
        values = (
            probabilities.home_win,
            probabilities.draw,
            probabilities.away_win,
        )
        predicted = labels[max(range(3), key=lambda index: values[index])]
        correct += int(predicted == outcome)
        actual_index = labels.index(outcome)
        targets = tuple(float(index == actual_index) for index in range(3))
        brier_total += sum(
            (probability - target) ** 2
            for probability, target in zip(values, targets, strict=True)
        )
        actual_probability = min(max(values[actual_index], epsilon), 1.0 - epsilon)
        log_loss_total -= log(actual_probability)
    sample_size = len(rows)
    return FootballProbabilityMetrics(
        sample_size=sample_size,
        accuracy=correct / sample_size,
        multiclass_brier=brier_total / sample_size,
        log_loss=log_loss_total / sample_size,
    )


def chronological_split(
    snapshots: Iterable[FootballFeatureSnapshot],
    *,
    validation_start: datetime,
    holdout_start: datetime,
) -> ChronologicalFootballSplit:
    """Partition snapshots without random shuffling or boundary overlap."""

    if validation_start >= holdout_start:
        raise ValueError("validation_start must be before holdout_start")
    ordered = sorted(snapshots, key=lambda item: (item.kickoff_utc, item.source_id))
    return ChronologicalFootballSplit(
        train=tuple(item for item in ordered if item.kickoff_utc < validation_start),
        validation=tuple(
            item
            for item in ordered
            if validation_start <= item.kickoff_utc < holdout_start
        ),
        holdout=tuple(item for item in ordered if item.kickoff_utc >= holdout_start),
    )


def _value(value: float | int | None, default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _feature_row(snapshot: FootballPredictionSnapshot) -> list[float]:
    competition = snapshot.competition_code
    return [
        _value(snapshot.home_last_10_goals_for),
        _value(snapshot.home_last_10_goals_against),
        _value(snapshot.home_last_10_points_per_match),
        _value(snapshot.away_last_10_goals_for),
        _value(snapshot.away_last_10_goals_against),
        _value(snapshot.away_last_10_points_per_match),
        min(_value(snapshot.home_days_rest), 14.0),
        min(_value(snapshot.away_days_rest), 14.0),
        min(snapshot.home_prior_matches, 10) / 10.0,
        min(snapshot.away_prior_matches, 10) / 10.0,
        float(snapshot.home_last_10_goals_for is None),
        float(snapshot.away_last_10_goals_for is None),
        float(competition == "PL"),
        float(competition == "PD"),
        float(competition == "SA"),
        float(competition == "DED"),
        float(competition == "CL"),
    ]


def _poisson_masses(rate: float, maximum: int = 12) -> list[float]:
    masses = [exp(-rate)]
    for goals in range(1, maximum + 1):
        masses.append(masses[-1] * rate / goals)
    return masses


def _logit(probability: float) -> float:
    epsilon = 1e-15
    bounded = min(max(probability, epsilon), 1.0 - epsilon)
    return log(bounded / (1.0 - bounded))


class FootballPoissonModel:
    """Estimate independent home and away goal rates from point-in-time features."""

    def __init__(self) -> None:
        self._home_pipeline: Pipeline | None = None
        self._away_pipeline: Pipeline | None = None
        self._result_calibrator: LogisticRegression | None = None
        self._totals_calibrator: LogisticRegression | None = None
        self._btts_calibrator: LogisticRegression | None = None
        self.training_cutoff: datetime | None = None
        self.calibration_cutoff: datetime | None = None

    def fit(
        self,
        snapshots: Iterable[FootballFeatureSnapshot],
        *,
        sample_weights: Iterable[float] | None = None,
    ) -> None:
        training = tuple(snapshots)
        if not training:
            raise ValueError("training snapshots cannot be empty")
        weights = tuple(sample_weights) if sample_weights is not None else None
        if weights is not None:
            if len(weights) != len(training):
                raise ValueError("sample_weights must match training snapshots")
            if any(weight <= 0.0 or weight > 1.0 for weight in weights):
                raise ValueError("sample_weights must be greater than 0 and at most 1")
        rows = [_feature_row(item) for item in training]
        home_pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                ("poisson", PoissonRegressor(alpha=1.0, max_iter=1000)),
            ]
        )
        away_pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                ("poisson", PoissonRegressor(alpha=1.0, max_iter=1000)),
            ]
        )
        fit_parameters = (
            {"poisson__sample_weight": weights} if weights is not None else {}
        )
        home_pipeline.fit(
            rows,
            [item.full_time_home_goals for item in training],
            **fit_parameters,
        )
        away_pipeline.fit(
            rows,
            [item.full_time_away_goals for item in training],
            **fit_parameters,
        )
        self._home_pipeline = home_pipeline
        self._away_pipeline = away_pipeline
        self._result_calibrator = None
        self._totals_calibrator = None
        self._btts_calibrator = None
        self.training_cutoff = max(item.kickoff_utc for item in training)
        self.calibration_cutoff = None

    def _raw_predict(self, snapshot: FootballPredictionSnapshot) -> FootballProbabilities:
        if self._home_pipeline is None or self._away_pipeline is None:
            raise RuntimeError("model has not been fitted")
        row = [_feature_row(snapshot)]
        home_rate = min(max(float(self._home_pipeline.predict(row)[0]), 0.05), 8.0)
        away_rate = min(max(float(self._away_pipeline.predict(row)[0]), 0.05), 8.0)
        home_masses = _poisson_masses(home_rate)
        away_masses = _poisson_masses(away_rate)
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        represented_mass = 0.0
        for home_goals, home_probability in enumerate(home_masses):
            for away_goals, away_probability in enumerate(away_masses):
                score_probability = home_probability * away_probability
                represented_mass += score_probability
                if home_goals > away_goals:
                    home_win += score_probability
                elif home_goals == away_goals:
                    draw += score_probability
                else:
                    away_win += score_probability
        home_win /= represented_mass
        draw /= represented_mass
        away_win /= represented_mass
        total_rate = home_rate + away_rate
        under_2_5 = exp(-total_rate) * (1.0 + total_rate + total_rate**2 / 2.0)
        btts = (1.0 - exp(-home_rate)) * (1.0 - exp(-away_rate))
        return FootballProbabilities(
            expected_home_goals=home_rate,
            expected_away_goals=away_rate,
            home_win=home_win,
            draw=draw,
            away_win=away_win,
            over_2_5=1.0 - under_2_5,
            both_teams_to_score=btts,
        )

    def calibrate(self, snapshots: Iterable[FootballFeatureSnapshot]) -> None:
        if self.training_cutoff is None:
            raise RuntimeError("model has not been fitted")
        validation = tuple(snapshots)
        if not validation:
            raise ValueError("calibration snapshots cannot be empty")
        if any(item.kickoff_utc <= self.training_cutoff for item in validation):
            raise ValueError("calibration snapshots must be after the training cutoff")
        raw = [self._raw_predict(item) for item in validation]
        result_targets = [
            0
            if item.full_time_home_goals > item.full_time_away_goals
            else 2
            if item.full_time_home_goals < item.full_time_away_goals
            else 1
            for item in validation
        ]
        totals_targets = [
            int(item.full_time_home_goals + item.full_time_away_goals >= 3)
            for item in validation
        ]
        btts_targets = [
            int(item.full_time_home_goals > 0 and item.full_time_away_goals > 0)
            for item in validation
        ]
        if set(result_targets) != {0, 1, 2}:
            raise ValueError("calibration snapshots must contain all 1X2 outcomes")
        if len(set(totals_targets)) < 2 or len(set(btts_targets)) < 2:
            raise ValueError("calibration snapshots must contain both binary outcomes")
        result_rows = [
            [
                log(max(item.home_win, 1e-15)),
                log(max(item.draw, 1e-15)),
                log(max(item.away_win, 1e-15)),
            ]
            for item in raw
        ]
        result_calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=0)
        result_calibrator.fit(result_rows, result_targets)
        totals_calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=0)
        totals_calibrator.fit(
            [[_logit(item.over_2_5)] for item in raw], totals_targets
        )
        btts_calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=0)
        btts_calibrator.fit(
            [[_logit(item.both_teams_to_score)] for item in raw], btts_targets
        )
        self._result_calibrator = result_calibrator
        self._totals_calibrator = totals_calibrator
        self._btts_calibrator = btts_calibrator
        self.calibration_cutoff = max(item.kickoff_utc for item in validation)

    def predict(self, snapshot: FootballPredictionSnapshot) -> FootballProbabilities:
        raw = self._raw_predict(snapshot)
        if (
            self._result_calibrator is None
            or self._totals_calibrator is None
            or self._btts_calibrator is None
        ):
            return raw
        result_row = [[
            log(max(raw.home_win, 1e-15)),
            log(max(raw.draw, 1e-15)),
            log(max(raw.away_win, 1e-15)),
        ]]
        result = self._result_calibrator.predict_proba(result_row)[0]
        over_2_5 = float(
            self._totals_calibrator.predict_proba([[_logit(raw.over_2_5)]])[0, 1]
        )
        btts = float(
            self._btts_calibrator.predict_proba(
                [[_logit(raw.both_teams_to_score)]]
            )[0, 1]
        )
        return FootballProbabilities(
            expected_home_goals=raw.expected_home_goals,
            expected_away_goals=raw.expected_away_goals,
            home_win=float(result[0]),
            draw=float(result[1]),
            away_win=float(result[2]),
            over_2_5=over_2_5,
            both_teams_to_score=btts,
        )
