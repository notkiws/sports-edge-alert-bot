"""Leakage-safe football feature snapshots."""

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from itertools import groupby

from sports_edge.domain.football import FootballMatch, MatchStatus

TeamKey = tuple[str, str]
H2HKey = tuple[str, str, str]
TeamResult = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class FootballFeatureSnapshot:
    source_id: str
    competition_code: str
    kickoff_utc: datetime
    home_team_id: str
    away_team_id: str
    home_prior_matches: int
    away_prior_matches: int
    home_last_10_goals_for: float | None
    home_last_10_goals_against: float | None
    home_last_10_points_per_match: float | None
    away_last_10_goals_for: float | None
    away_last_10_goals_against: float | None
    away_last_10_points_per_match: float | None
    home_days_rest: int | None
    away_days_rest: int | None
    prior_h2h_matches: int
    full_time_home_goals: int
    full_time_away_goals: int


def _average(results: deque[TeamResult], index: int) -> float | None:
    if not results:
        return None
    return sum(result[index] for result in results) / len(results)


def _days_rest(last_played: date | None, current: date) -> int | None:
    if last_played is None:
        return None
    return (current - last_played).days


def _points(goals_for: int, goals_against: int) -> int:
    if goals_for > goals_against:
        return 3
    if goals_for == goals_against:
        return 1
    return 0


def _keys(match: FootballMatch) -> tuple[TeamKey, TeamKey, H2HKey]:
    competition_id = match.competition.source_id
    team_a, team_b = sorted((match.home_team_id, match.away_team_id))
    return (
        (competition_id, match.home_team_id),
        (competition_id, match.away_team_id),
        (competition_id, team_a, team_b),
    )


class FootballFeatureBuilder:
    """Build competition-scoped features from completed prior dates."""

    def build(
        self, matches: Iterable[FootballMatch]
    ) -> tuple[FootballFeatureSnapshot, ...]:
        histories: dict[TeamKey, deque[TeamResult]] = defaultdict(lambda: deque(maxlen=10))
        total_matches: dict[TeamKey, int] = defaultdict(int)
        last_played: dict[TeamKey, date] = {}
        h2h_counts: dict[H2HKey, int] = defaultdict(int)
        eligible = [
            match
            for match in matches
            if match.status is MatchStatus.FINISHED and match.score.full_time is not None
        ]
        ordered = sorted(eligible, key=lambda item: (item.kickoff_utc, item.source_id))
        snapshots: list[FootballFeatureSnapshot] = []
        for _, date_group in groupby(ordered, key=lambda item: item.kickoff_utc.date()):
            date_matches = list(date_group)
            for match in date_matches:
                snapshots.append(
                    self._snapshot(
                        match,
                        histories,
                        total_matches,
                        last_played,
                        h2h_counts,
                    )
                )
            for match in date_matches:
                self._update(match, histories, total_matches, last_played, h2h_counts)
        return tuple(snapshots)

    def _snapshot(
        self,
        match: FootballMatch,
        histories: dict[TeamKey, deque[TeamResult]],
        total_matches: dict[TeamKey, int],
        last_played: dict[TeamKey, date],
        h2h_counts: dict[H2HKey, int],
    ) -> FootballFeatureSnapshot:
        full_time = match.score.full_time
        if full_time is None:
            raise ValueError("finished feature match requires a full-time score")
        home_key, away_key, h2h_key = _keys(match)
        home_history = histories[home_key]
        away_history = histories[away_key]
        return FootballFeatureSnapshot(
            source_id=match.source_id,
            competition_code=match.competition.code,
            kickoff_utc=match.kickoff_utc,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            home_prior_matches=total_matches[home_key],
            away_prior_matches=total_matches[away_key],
            home_last_10_goals_for=_average(home_history, 0),
            home_last_10_goals_against=_average(home_history, 1),
            home_last_10_points_per_match=_average(home_history, 2),
            away_last_10_goals_for=_average(away_history, 0),
            away_last_10_goals_against=_average(away_history, 1),
            away_last_10_points_per_match=_average(away_history, 2),
            home_days_rest=_days_rest(last_played.get(home_key), match.kickoff_utc.date()),
            away_days_rest=_days_rest(last_played.get(away_key), match.kickoff_utc.date()),
            prior_h2h_matches=h2h_counts[h2h_key],
            full_time_home_goals=full_time[0],
            full_time_away_goals=full_time[1],
        )

    def _update(
        self,
        match: FootballMatch,
        histories: dict[TeamKey, deque[TeamResult]],
        total_matches: dict[TeamKey, int],
        last_played: dict[TeamKey, date],
        h2h_counts: dict[H2HKey, int],
    ) -> None:
        full_time = match.score.full_time
        if full_time is None:
            raise ValueError("finished feature match requires a full-time score")
        home_key, away_key, h2h_key = _keys(match)
        home_goals, away_goals = full_time
        histories[home_key].append(
            (home_goals, away_goals, _points(home_goals, away_goals))
        )
        histories[away_key].append(
            (away_goals, home_goals, _points(away_goals, home_goals))
        )
        total_matches[home_key] += 1
        total_matches[away_key] += 1
        last_played[home_key] = match.kickoff_utc.date()
        last_played[away_key] = match.kickoff_utc.date()
        h2h_counts[h2h_key] += 1
