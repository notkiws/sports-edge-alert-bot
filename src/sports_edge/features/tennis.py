"""Leakage-safe tennis feature snapshots."""

from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from itertools import groupby
from math import pow

from sports_edge.domain.tennis import (
    HistoricalTennisMatch,
    TennisMatchStatus,
    TennisTour,
    TournamentLevel,
)

INITIAL_ELO = 1500.0
ELO_K_FACTOR = 32.0
PlayerKey = tuple[TennisTour, str]
SurfaceKey = tuple[TennisTour, str, str]
H2HKey = tuple[TennisTour, str, str]


@dataclass(frozen=True, slots=True)
class TennisFeatureSnapshot:
    source_file: str
    source_row: int
    played_on: date
    tour: TennisTour
    tournament: str
    level: TournamentLevel
    surface: str
    player_a: str
    player_b: str
    player_a_won: bool
    player_a_rank: int | None
    player_b_rank: int | None
    rank_advantage_a: int | None
    overall_elo_difference: float
    surface_elo_difference: float
    player_a_overall_matches: int
    player_b_overall_matches: int
    player_a_last_10_win_rate: float | None
    player_b_last_10_win_rate: float | None
    player_a_surface_last_10_win_rate: float | None
    player_b_surface_last_10_win_rate: float | None
    player_a_days_rest: int | None
    player_b_days_rest: int | None
    player_a_recent_retirements: int
    player_b_recent_retirements: int
    prior_h2h_matches: int
    player_a_h2h_win_rate: float | None


def _win_rate(results: deque[bool]) -> float | None:
    if not results:
        return None
    return sum(results) / len(results)


def _expected_score(rating: float, opponent_rating: float) -> float:
    return 1.0 / (1.0 + pow(10.0, (opponent_rating - rating) / 400.0))


def _days_rest(last_played: date | None, current_date: date) -> int | None:
    if last_played is None:
        return None
    return (current_date - last_played).days


class TennisFeatureBuilder:
    """Build features from information available strictly before each match day."""

    def build(
        self, matches: Iterable[HistoricalTennisMatch]
    ) -> tuple[TennisFeatureSnapshot, ...]:
        ordered = sorted(
            matches,
            key=lambda item: (item.played_on, item.source_file, item.source_row),
        )
        overall_elo: dict[PlayerKey, float] = defaultdict(lambda: INITIAL_ELO)
        surface_elo: dict[SurfaceKey, float] = defaultdict(lambda: INITIAL_ELO)
        overall_form: dict[PlayerKey, deque[bool]] = defaultdict(lambda: deque(maxlen=10))
        surface_form: dict[SurfaceKey, deque[bool]] = defaultdict(lambda: deque(maxlen=10))
        retirement_history: dict[PlayerKey, deque[bool]] = defaultdict(
            lambda: deque(maxlen=10)
        )
        overall_matches: dict[PlayerKey, int] = defaultdict(int)
        last_played: dict[PlayerKey, date] = {}
        h2h: dict[H2HKey, tuple[int, int]] = {}
        snapshots: list[TennisFeatureSnapshot] = []

        for _, day_group in groupby(ordered, key=lambda item: item.played_on):
            day_matches = list(day_group)
            for match in day_matches:
                if match.status is TennisMatchStatus.COMPLETED:
                    snapshots.append(
                        self._snapshot(
                            match,
                            overall_elo,
                            surface_elo,
                            overall_form,
                            surface_form,
                            overall_matches,
                            last_played,
                            retirement_history,
                            h2h,
                        )
                    )
            for match in day_matches:
                self._update(
                    match,
                    overall_elo,
                    surface_elo,
                    overall_form,
                    surface_form,
                    overall_matches,
                    last_played,
                    retirement_history,
                    h2h,
                )
        return tuple(snapshots)

    def _snapshot(
        self,
        match: HistoricalTennisMatch,
        overall_elo: dict[PlayerKey, float],
        surface_elo: dict[SurfaceKey, float],
        overall_form: dict[PlayerKey, deque[bool]],
        surface_form: dict[SurfaceKey, deque[bool]],
        overall_matches: dict[PlayerKey, int],
        last_played: dict[PlayerKey, date],
        retirement_history: dict[PlayerKey, deque[bool]],
        h2h: dict[H2HKey, tuple[int, int]],
    ) -> TennisFeatureSnapshot:
        player_a, player_b = sorted((match.winner, match.loser), key=str.casefold)
        player_a_won = player_a == match.winner
        player_a_rank = match.winner_rank if player_a_won else match.loser_rank
        player_b_rank = match.loser_rank if player_a_won else match.winner_rank
        key_a = (match.tour, player_a)
        key_b = (match.tour, player_b)
        surface_a = (match.tour, player_a, match.surface.casefold())
        surface_b = (match.tour, player_b, match.surface.casefold())
        h2h_key = (match.tour, player_a, player_b)
        h2h_count, player_a_h2h_wins = h2h.get(h2h_key, (0, 0))
        return TennisFeatureSnapshot(
            source_file=match.source_file,
            source_row=match.source_row,
            played_on=match.played_on,
            tour=match.tour,
            tournament=match.tournament,
            level=match.level,
            surface=match.surface,
            player_a=player_a,
            player_b=player_b,
            player_a_won=player_a_won,
            player_a_rank=player_a_rank,
            player_b_rank=player_b_rank,
            rank_advantage_a=(
                player_b_rank - player_a_rank
                if player_a_rank is not None and player_b_rank is not None
                else None
            ),
            overall_elo_difference=overall_elo[key_a] - overall_elo[key_b],
            surface_elo_difference=surface_elo[surface_a] - surface_elo[surface_b],
            player_a_overall_matches=overall_matches[key_a],
            player_b_overall_matches=overall_matches[key_b],
            player_a_last_10_win_rate=_win_rate(overall_form[key_a]),
            player_b_last_10_win_rate=_win_rate(overall_form[key_b]),
            player_a_surface_last_10_win_rate=_win_rate(surface_form[surface_a]),
            player_b_surface_last_10_win_rate=_win_rate(surface_form[surface_b]),
            player_a_days_rest=_days_rest(last_played.get(key_a), match.played_on),
            player_b_days_rest=_days_rest(last_played.get(key_b), match.played_on),
            player_a_recent_retirements=sum(retirement_history[key_a]),
            player_b_recent_retirements=sum(retirement_history[key_b]),
            prior_h2h_matches=h2h_count,
            player_a_h2h_win_rate=(
                player_a_h2h_wins / h2h_count if h2h_count >= 3 else None
            ),
        )

    def _update(
        self,
        match: HistoricalTennisMatch,
        overall_elo: dict[PlayerKey, float],
        surface_elo: dict[SurfaceKey, float],
        overall_form: dict[PlayerKey, deque[bool]],
        surface_form: dict[SurfaceKey, deque[bool]],
        overall_matches: dict[PlayerKey, int],
        last_played: dict[PlayerKey, date],
        retirement_history: dict[PlayerKey, deque[bool]],
        h2h: dict[H2HKey, tuple[int, int]],
    ) -> None:
        winner_key = (match.tour, match.winner)
        loser_key = (match.tour, match.loser)
        if match.status is TennisMatchStatus.RETIRED:
            retirement_history[winner_key].append(False)
            retirement_history[loser_key].append(True)
            last_played[winner_key] = match.played_on
            last_played[loser_key] = match.played_on
            return
        if match.status is not TennisMatchStatus.COMPLETED:
            return
        retirement_history[winner_key].append(False)
        retirement_history[loser_key].append(False)
        surface = match.surface.casefold()
        winner_surface = (match.tour, match.winner, surface)
        loser_surface = (match.tour, match.loser, surface)

        winner_expected = _expected_score(overall_elo[winner_key], overall_elo[loser_key])
        rating_change = ELO_K_FACTOR * (1.0 - winner_expected)
        overall_elo[winner_key] += rating_change
        overall_elo[loser_key] -= rating_change

        surface_expected = _expected_score(
            surface_elo[winner_surface], surface_elo[loser_surface]
        )
        surface_change = ELO_K_FACTOR * (1.0 - surface_expected)
        surface_elo[winner_surface] += surface_change
        surface_elo[loser_surface] -= surface_change

        overall_form[winner_key].append(True)
        overall_form[loser_key].append(False)
        surface_form[winner_surface].append(True)
        surface_form[loser_surface].append(False)
        overall_matches[winner_key] += 1
        overall_matches[loser_key] += 1
        last_played[winner_key] = match.played_on
        last_played[loser_key] = match.played_on

        player_a, player_b = sorted((match.winner, match.loser), key=str.casefold)
        h2h_key = (match.tour, player_a, player_b)
        count, player_a_wins = h2h.get(h2h_key, (0, 0))
        h2h[h2h_key] = (count + 1, player_a_wins + int(match.winner == player_a))
