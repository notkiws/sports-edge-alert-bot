"""Tennis probability model and chronological partitioning."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from math import log

from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]

from sports_edge.features.tennis import TennisFeatureSnapshot


@dataclass(frozen=True, slots=True)
class ChronologicalTennisSplit:
    train: tuple[TennisFeatureSnapshot, ...]
    validation: tuple[TennisFeatureSnapshot, ...]
    holdout: tuple[TennisFeatureSnapshot, ...]


@dataclass(frozen=True, slots=True)
class ProbabilityMetrics:
    sample_size: int
    hit_rate: float
    brier_score: float
    log_loss: float


def chronological_split(
    snapshots: Iterable[TennisFeatureSnapshot],
    *,
    validation_start: date,
    holdout_start: date,
) -> ChronologicalTennisSplit:
    if validation_start >= holdout_start:
        raise ValueError("validation_start must be before holdout_start")
    ordered = sorted(
        snapshots,
        key=lambda item: (item.played_on, item.source_file, item.source_row),
    )
    return ChronologicalTennisSplit(
        train=tuple(item for item in ordered if item.played_on < validation_start),
        validation=tuple(
            item for item in ordered if validation_start <= item.played_on < holdout_start
        ),
        holdout=tuple(item for item in ordered if item.played_on >= holdout_start),
    )


def evaluate_probabilities(
    predictions: Iterable[tuple[float, bool]],
) -> ProbabilityMetrics:
    observations = tuple(predictions)
    if not observations:
        raise ValueError("predictions cannot be empty")
    epsilon = 1e-15
    hits = 0
    squared_errors = 0.0
    log_loss_total = 0.0
    for probability, outcome in observations:
        if not 0.0 <= probability <= 1.0:
            raise ValueError("probability must be between zero and one")
        target = float(outcome)
        hits += int((probability >= 0.5) is outcome)
        squared_errors += (probability - target) ** 2
        bounded = min(max(probability, epsilon), 1.0 - epsilon)
        log_loss_total -= target * log(bounded) + (1.0 - target) * log(1.0 - bounded)
    sample_size = len(observations)
    return ProbabilityMetrics(
        sample_size=sample_size,
        hit_rate=hits / sample_size,
        brier_score=squared_errors / sample_size,
        log_loss=log_loss_total / sample_size,
    )


def _difference(left: float | None, right: float | None) -> float:
    return (left if left is not None else 0.5) - (right if right is not None else 0.5)


def _logit(probability: float) -> float:
    epsilon = 1e-15
    bounded = min(max(probability, epsilon), 1.0 - epsilon)
    return log(bounded / (1.0 - bounded))


def _feature_row(snapshot: TennisFeatureSnapshot) -> list[float]:
    surface = snapshot.surface.casefold()
    return [
        float(snapshot.rank_advantage_a or 0),
        float(snapshot.player_a_rank is None or snapshot.player_b_rank is None),
        snapshot.overall_elo_difference,
        snapshot.surface_elo_difference,
        _difference(
            snapshot.player_a_last_10_win_rate,
            snapshot.player_b_last_10_win_rate,
        ),
        _difference(
            snapshot.player_a_surface_last_10_win_rate,
            snapshot.player_b_surface_last_10_win_rate,
        ),
        float((snapshot.player_a_days_rest or 0) - (snapshot.player_b_days_rest or 0)),
        float(snapshot.player_a_days_rest is None or snapshot.player_b_days_rest is None),
        float(
            snapshot.player_b_recent_retirements
            - snapshot.player_a_recent_retirements
        ),
        (snapshot.player_a_h2h_win_rate or 0.5) - 0.5,
        float(snapshot.player_a_h2h_win_rate is not None),
        float(snapshot.tour.value == "WTA"),
        float(surface == "clay"),
        float(surface == "grass"),
        float(snapshot.level.value == "1000"),
        float(snapshot.level.value == "FINALS"),
        float(snapshot.level.value == "GRAND_SLAM"),
    ]


class TennisLogisticModel:
    """Regularized point-in-time tennis match-winner baseline."""

    def __init__(self) -> None:
        self._pipeline: Pipeline | None = None
        self._calibrator: LogisticRegression | None = None
        self.training_cutoff: date | None = None
        self.calibration_cutoff: date | None = None

    def fit(self, snapshots: Iterable[TennisFeatureSnapshot]) -> None:
        training = tuple(snapshots)
        if not training:
            raise ValueError("training snapshots cannot be empty")
        targets = [int(item.player_a_won) for item in training]
        if len(set(targets)) < 2:
            raise ValueError("training snapshots must contain both outcomes")
        pipeline = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(C=1.0, max_iter=1000, random_state=0),
                ),
            ]
        )
        pipeline.fit([_feature_row(item) for item in training], targets)
        self._pipeline = pipeline
        self._calibrator = None
        self.training_cutoff = max(item.played_on for item in training)
        self.calibration_cutoff = None

    def calibrate(self, snapshots: Iterable[TennisFeatureSnapshot]) -> None:
        if self._pipeline is None or self.training_cutoff is None:
            raise RuntimeError("model has not been fitted")
        validation = tuple(snapshots)
        if not validation:
            raise ValueError("calibration snapshots cannot be empty")
        if any(item.played_on <= self.training_cutoff for item in validation):
            raise ValueError("calibration snapshots must be after the training cutoff")
        targets = [int(item.player_a_won) for item in validation]
        if len(set(targets)) < 2:
            raise ValueError("calibration snapshots must contain both outcomes")
        raw_logits = [[_logit(self._raw_probability(item))] for item in validation]
        calibrator = LogisticRegression(C=1.0, max_iter=1000, random_state=0)
        calibrator.fit(raw_logits, targets)
        self._calibrator = calibrator
        self.calibration_cutoff = max(item.played_on for item in validation)

    def _raw_probability(self, snapshot: TennisFeatureSnapshot) -> float:
        if self._pipeline is None:
            raise RuntimeError("model has not been fitted")
        return float(self._pipeline.predict_proba([_feature_row(snapshot)])[0, 1])

    def predict_player_a_probability(self, snapshot: TennisFeatureSnapshot) -> float:
        raw_probability = self._raw_probability(snapshot)
        if self._calibrator is None:
            return raw_probability
        return float(self._calibrator.predict_proba([[_logit(raw_probability)]])[0, 1])
