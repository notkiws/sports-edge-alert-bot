"""Runtime football qualification for unsent report generation."""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from sports_edge.config import Settings
from sports_edge.domain.football import FootballMatch, MatchStatus
from sports_edge.features.football import (
    FootballFeatureBuilder,
    UpcomingFootballFeatureSnapshot,
)
from sports_edge.models.football import FootballPoissonModel, FootballProbabilities
from sports_edge.providers.football_data_org import FootballDataOrgAdapter
from sports_edge.reporting.telegram import FootballReportSelection

_MARKET_EVIDENCE = {
    "1X2": (0.7128, 296),
    "TOTAL_2_5": (0.6735, 294),
}
_RESULT_ID = {
    "HOME": "TUAN RUMAH",
    "DRAW": "SERI",
    "AWAY": "TANDANG",
}


@dataclass(frozen=True, slots=True)
class RuntimeForecastRun:
    history_size: int
    training_size: int
    calibration_size: int
    fixture_size: int
    selections: tuple[FootballReportSelection, ...]


class FixtureClient(Protocol):
    def fetch_competition_matches_between(
        self,
        competition_code: str,
        date_from: date,
        date_to: date,
    ) -> Mapping[str, Any]: ...


def load_historical_matches(cache_root: Path) -> tuple[FootballMatch, ...]:
    """Normalize immutable year/competition cache files for model fitting."""

    adapter = FootballDataOrgAdapter()
    matches: list[FootballMatch] = []
    for path in sorted(cache_root.glob("[0-9][0-9][0-9][0-9]/*.json")):
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("matches"), list):
            raise ValueError(f"invalid football cache payload: {path}")
        for item in payload["matches"]:
            if not isinstance(item, dict):
                raise ValueError(f"invalid football match payload: {path}")
            matches.append(adapter.normalize_match(item))
    return tuple(sorted(matches, key=lambda item: (item.kickoff_utc, item.source_id)))


def collect_upcoming_fixtures(
    client: FixtureClient,
    competition_codes: Iterable[str],
    *,
    date_from: date,
    date_to: date,
    raw_snapshot_path: Path | None = None,
) -> tuple[FootballMatch, ...]:
    """Fetch and normalize currently scheduled fixtures for enabled competitions."""

    adapter = FootballDataOrgAdapter()
    fixtures: list[FootballMatch] = []
    raw_by_competition: dict[str, Mapping[str, Any]] = {}
    for competition_code in competition_codes:
        payload = client.fetch_competition_matches_between(
            competition_code,
            date_from,
            date_to,
        )
        raw_by_competition[competition_code] = payload
        raw_matches = payload.get("matches")
        if not isinstance(raw_matches, list):
            raise ValueError("football fixture response must contain a matches list")
        for item in raw_matches:
            if not isinstance(item, dict):
                raise ValueError("football fixture response contains an invalid match")
            if item.get("status") not in {
                MatchStatus.SCHEDULED.value,
                MatchStatus.TIMED.value,
            }:
                continue
            match = adapter.normalize_match(item)
            fixtures.append(match)
    if raw_snapshot_path is not None:
        raw_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = raw_snapshot_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                    "competitions": raw_by_competition,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(raw_snapshot_path)
    return tuple(sorted(fixtures, key=lambda item: (item.kickoff_utc, item.source_id)))


def _grade(snapshot: UpcomingFootballFeatureSnapshot) -> str:
    minimum_history = min(snapshot.home_prior_matches, snapshot.away_prior_matches)
    if minimum_history >= 10:
        return "A"
    if minimum_history >= 5:
        return "B"
    return "C"


def _grade_c_reasons(
    snapshot: UpcomingFootballFeatureSnapshot,
) -> tuple[str, str]:
    counts = (
        f"{snapshot.home_team_name}: {snapshot.home_prior_matches}, "
        f"{snapshot.away_team_name}: {snapshot.away_prior_matches}"
    )
    return (
        f"Limited prior-match history ({counts}).",
        f"Riwayat pertandingan sebelumnya terbatas ({counts}).",
    )


def qualify_runtime_forecasts(
    snapshot: UpcomingFootballFeatureSnapshot,
    probabilities: FootballProbabilities,
) -> tuple[FootballReportSelection, ...]:
    """Map frozen qualifying probabilities into bilingual report selections."""

    settings = Settings()
    result_probabilities = {
        "HOME": probabilities.home_win,
        "DRAW": probabilities.draw,
        "AWAY": probabilities.away_win,
    }
    result_selection = max(
        result_probabilities,
        key=lambda selection: result_probabilities[selection],
    )
    total_selection = "OVER 2.5" if probabilities.over_2_5 >= 0.5 else "UNDER 2.5"
    total_probability = max(probabilities.over_2_5, 1.0 - probabilities.over_2_5)
    candidates = (
        (
            "1X2",
            result_selection,
            _RESULT_ID[result_selection],
            result_probabilities[result_selection],
        ),
        (
            "TOTAL_2_5",
            total_selection,
            "DI ATAS 2.5" if total_selection == "OVER 2.5" else "DI BAWAH 2.5",
            total_probability,
        ),
    )
    selections: list[FootballReportSelection] = []
    grade = _grade(snapshot)
    grade_reason_en, grade_reason_id = _grade_c_reasons(snapshot)
    for market, selection_en, selection_id, probability in candidates:
        if market not in settings.football_enabled_markets:
            continue
        if probability < settings.football_probability_floor:
            continue
        hit_rate, sample_size = _MARKET_EVIDENCE[market]
        selections.append(
            FootballReportSelection(
                competition=snapshot.competition_name,
                kickoff_utc=snapshot.kickoff_utc,
                home_team=snapshot.home_team_name,
                away_team=snapshot.away_team_name,
                market=market,
                selection_en=selection_en,
                selection_id=selection_id,
                probability=probability,
                historical_hit_rate=hit_rate,
                historical_sample_size=sample_size,
                grade=grade,
                reasoning_en=grade_reason_en,
                reasoning_id=grade_reason_id,
                warning_en="Probability forecast only; odds were not evaluated.",
                warning_id="Hanya prediksi probabilitas; odds tidak dievaluasi.",
            )
        )
    selections.sort(key=lambda item: (-item.probability, item.market, item.selection_en))
    return tuple(selections[:3])


def produce_runtime_forecasts(
    history: Iterable[FootballMatch],
    fixtures: Iterable[FootballMatch],
) -> RuntimeForecastRun:
    """Fit chronologically, calibrate on the latest date block, and predict fixtures."""

    historical_matches = tuple(history)
    upcoming_matches = tuple(fixtures)
    builder = FootballFeatureBuilder()
    snapshots = builder.build(historical_matches)
    unique_dates = sorted({item.kickoff_utc.date() for item in snapshots})
    if len(unique_dates) < 2:
        raise ValueError("football history must span at least two dates")
    calibration_index = min(
        max(1, int(len(unique_dates) * 0.8)),
        len(unique_dates) - 1,
    )
    calibration_start = unique_dates[calibration_index]
    training = tuple(
        item for item in snapshots if item.kickoff_utc.date() < calibration_start
    )
    calibration = tuple(
        item for item in snapshots if item.kickoff_utc.date() >= calibration_start
    )
    model = FootballPoissonModel()
    model.fit(training)
    model.calibrate(calibration)
    upcoming_snapshots = builder.build_upcoming(historical_matches, upcoming_matches)
    selections = tuple(
        selection
        for snapshot in upcoming_snapshots
        for selection in qualify_runtime_forecasts(snapshot, model.predict(snapshot))
    )
    return RuntimeForecastRun(
        history_size=len(snapshots),
        training_size=len(training),
        calibration_size=len(calibration),
        fixture_size=len(upcoming_snapshots),
        selections=selections,
    )


def _report_record(selection: FootballReportSelection) -> dict[str, object]:
    return {
        "competition": selection.competition,
        "kickoff_utc": selection.kickoff_utc.isoformat(),
        "home_team": selection.home_team,
        "away_team": selection.away_team,
        "market": selection.market,
        "selection_en": selection.selection_en,
        "selection_id": selection.selection_id,
        "probability": selection.probability,
        "historical_hit_rate": selection.historical_hit_rate,
        "historical_sample_size": selection.historical_sample_size,
        "grade": selection.grade,
        "reasoning_en": selection.reasoning_en,
        "reasoning_id": selection.reasoning_id,
        "warning_en": selection.warning_en,
        "warning_id": selection.warning_id,
    }


def write_runtime_forecasts(
    destination: Path,
    selections: Iterable[FootballReportSelection],
    *,
    generated_at_utc: datetime,
) -> None:
    """Atomically write scheduler-compatible qualified football forecasts."""

    if generated_at_utc.utcoffset() != timedelta(0):
        raise ValueError("generated_at_utc must be timezone-aware UTC")
    payload = {
        "generated_at_utc": generated_at_utc.isoformat(),
        "model": "football-poisson-v1",
        "football": [_report_record(selection) for selection in selections],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
