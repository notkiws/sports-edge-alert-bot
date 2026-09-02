"""Football forecast qualification and statistical summaries."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from math import log, sqrt

from sports_edge.config import Settings
from sports_edge.features.football import FootballFeatureSnapshot
from sports_edge.models.football import FootballPoissonModel, FootballProbabilities


@dataclass(frozen=True, slots=True)
class QualifiedFootballForecast:
    source_id: str
    competition_code: str
    market: str
    selection: str
    probability: float
    correct: bool


@dataclass(frozen=True, slots=True)
class ForecastMetrics:
    sample_size: int
    hit_rate: float
    wilson_low: float
    wilson_high: float
    brier_score: float
    log_loss: float
    expected_calibration_error: float


@dataclass(frozen=True, slots=True)
class FootballMarketMetrics:
    market: str
    metrics: ForecastMetrics


@dataclass(frozen=True, slots=True)
class FootballFoldResult:
    train_size: int
    calibration_size: int
    evaluation_size: int
    forecasts: tuple[QualifiedFootballForecast, ...]
    overall_metrics: ForecastMetrics | None
    market_metrics: tuple[FootballMarketMetrics, ...]


def qualify_forecasts(
    snapshot: FootballFeatureSnapshot,
    probabilities: FootballProbabilities,
    *,
    probability_floor: float,
    maximum_forecasts: int = 3,
    enabled_markets: Iterable[str] | None = None,
) -> tuple[QualifiedFootballForecast, ...]:
    """Return individually qualifying, non-duplicate options ranked by probability."""

    if not 0.0 < probability_floor < 1.0:
        raise ValueError("probability_floor must be between 0 and 1")
    if maximum_forecasts < 1:
        raise ValueError("maximum_forecasts must be positive")
    actual_result = (
        "HOME"
        if snapshot.full_time_home_goals > snapshot.full_time_away_goals
        else "AWAY"
        if snapshot.full_time_home_goals < snapshot.full_time_away_goals
        else "DRAW"
    )
    result_values = {
        "HOME": probabilities.home_win,
        "DRAW": probabilities.draw,
        "AWAY": probabilities.away_win,
    }
    result_selection = max(
        result_values,
        key=lambda selection: result_values[selection],
    )
    total_is_over = snapshot.full_time_home_goals + snapshot.full_time_away_goals >= 3
    total_selection = "OVER" if probabilities.over_2_5 >= 0.5 else "UNDER"
    total_probability = max(probabilities.over_2_5, 1.0 - probabilities.over_2_5)
    btts_actual = (
        snapshot.full_time_home_goals > 0 and snapshot.full_time_away_goals > 0
    )
    btts_selection = "YES" if probabilities.both_teams_to_score >= 0.5 else "NO"
    btts_probability = max(
        probabilities.both_teams_to_score,
        1.0 - probabilities.both_teams_to_score,
    )
    candidates = (
        QualifiedFootballForecast(
            source_id=snapshot.source_id,
            competition_code=snapshot.competition_code,
            market="1X2",
            selection=result_selection,
            probability=result_values[result_selection],
            correct=result_selection == actual_result,
        ),
        QualifiedFootballForecast(
            source_id=snapshot.source_id,
            competition_code=snapshot.competition_code,
            market="TOTAL_2_5",
            selection=total_selection,
            probability=total_probability,
            correct=total_is_over if total_selection == "OVER" else not total_is_over,
        ),
        QualifiedFootballForecast(
            source_id=snapshot.source_id,
            competition_code=snapshot.competition_code,
            market="BTTS",
            selection=btts_selection,
            probability=btts_probability,
            correct=btts_actual if btts_selection == "YES" else not btts_actual,
        ),
    )
    allowed = (
        frozenset(enabled_markets)
        if enabled_markets is not None
        else frozenset(Settings().football_enabled_markets)
    )
    qualified = [
        item
        for item in candidates
        if item.market in allowed and item.probability >= probability_floor
    ]
    qualified.sort(key=lambda item: (-item.probability, item.market, item.selection))
    return tuple(qualified[:maximum_forecasts])


def summarize_forecasts(
    forecasts: Iterable[QualifiedFootballForecast],
) -> ForecastMetrics:
    """Summarize selected forecasts with uncertainty and ten-bin calibration error."""

    rows = tuple(forecasts)
    if not rows:
        raise ValueError("forecasts cannot be empty")
    sample_size = len(rows)
    outcomes = [float(item.correct) for item in rows]
    hit_rate = sum(outcomes) / sample_size
    z = 1.959963984540054
    denominator = 1.0 + z**2 / sample_size
    center = (hit_rate + z**2 / (2.0 * sample_size)) / denominator
    margin = (
        z
        * sqrt(
            hit_rate * (1.0 - hit_rate) / sample_size
            + z**2 / (4.0 * sample_size**2)
        )
        / denominator
    )
    brier = sum(
        (item.probability - outcome) ** 2
        for item, outcome in zip(rows, outcomes, strict=True)
    ) / sample_size
    epsilon = 1e-15
    log_loss = -sum(
        outcome * log(min(max(item.probability, epsilon), 1.0 - epsilon))
        + (1.0 - outcome)
        * log(min(max(1.0 - item.probability, epsilon), 1.0 - epsilon))
        for item, outcome in zip(rows, outcomes, strict=True)
    ) / sample_size
    bins: dict[int, list[QualifiedFootballForecast]] = {}
    for item in rows:
        bins.setdefault(min(int(item.probability * 10), 9), []).append(item)
    calibration_error = sum(
        len(items)
        / sample_size
        * abs(
            sum(item.probability for item in items) / len(items)
            - sum(item.correct for item in items) / len(items)
        )
        for items in bins.values()
    )
    return ForecastMetrics(
        sample_size=sample_size,
        hit_rate=hit_rate,
        wilson_low=center - margin,
        wilson_high=center + margin,
        brier_score=brier,
        log_loss=log_loss,
        expected_calibration_error=calibration_error,
    )


def run_football_fold(
    snapshots: Iterable[FootballFeatureSnapshot],
    *,
    calibration_start: datetime,
    evaluation_start: datetime,
    evaluation_end: datetime,
    probability_floor: float,
    training_sample_weights: Iterable[float] | None = None,
) -> FootballFoldResult:
    """Fit, calibrate, and evaluate one non-overlapping chronological fold."""

    if not calibration_start < evaluation_start < evaluation_end:
        raise ValueError("fold boundaries must be strictly increasing")
    ordered = sorted(snapshots, key=lambda item: (item.kickoff_utc, item.source_id))
    training = tuple(item for item in ordered if item.kickoff_utc < calibration_start)
    calibration = tuple(
        item
        for item in ordered
        if calibration_start <= item.kickoff_utc < evaluation_start
    )
    evaluation = tuple(
        item
        for item in ordered
        if evaluation_start <= item.kickoff_utc < evaluation_end
    )
    if not training or not calibration or not evaluation:
        raise ValueError("every fold period must contain snapshots")
    model = FootballPoissonModel()
    model.fit(training, sample_weights=training_sample_weights)
    model.calibrate(calibration)
    forecasts = tuple(
        forecast
        for snapshot in evaluation
        for forecast in qualify_forecasts(
            snapshot,
            model.predict(snapshot),
            probability_floor=probability_floor,
        )
    )
    markets = sorted({forecast.market for forecast in forecasts})
    market_metrics = tuple(
        FootballMarketMetrics(
            market=market,
            metrics=summarize_forecasts(
                forecast for forecast in forecasts if forecast.market == market
            ),
        )
        for market in markets
    )
    return FootballFoldResult(
        train_size=len(training),
        calibration_size=len(calibration),
        evaluation_size=len(evaluation),
        forecasts=forecasts,
        overall_metrics=summarize_forecasts(forecasts) if forecasts else None,
        market_metrics=market_metrics,
    )
