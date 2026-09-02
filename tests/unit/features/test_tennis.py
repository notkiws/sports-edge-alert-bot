from datetime import date

from sports_edge.domain.tennis import (
    HistoricalTennisMatch,
    TennisMatchStatus,
    TennisTour,
    TournamentLevel,
)
from sports_edge.features.tennis import TennisFeatureBuilder


def match(
    *,
    played_on: date,
    winner: str,
    loser: str,
    winner_rank: int = 10,
    loser_rank: int = 20,
    surface: str = "Hard",
    source_row: int = 2,
    status: TennisMatchStatus = TennisMatchStatus.COMPLETED,
) -> HistoricalTennisMatch:
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
        surface=surface,
        round_name="1st Round",
        winner=winner,
        loser=loser,
        winner_rank=winner_rank,
        loser_rank=loser_rank,
        status=status,
    )


def test_first_match_uses_neutral_prematch_state_and_outcome_independent_orientation() -> None:
    historical_match = match(
        played_on=date(2025, 1, 1),
        winner="Zulu Z.",
        loser="Alpha A.",
        winner_rank=8,
        loser_rank=20,
    )

    snapshot = TennisFeatureBuilder().build([historical_match])[0]

    assert snapshot.player_a == "Alpha A."
    assert snapshot.player_b == "Zulu Z."
    assert snapshot.player_a_won is False
    assert snapshot.player_a_rank == 20
    assert snapshot.player_b_rank == 8
    assert snapshot.rank_advantage_a == -12
    assert snapshot.overall_elo_difference == 0.0
    assert snapshot.surface_elo_difference == 0.0
    assert snapshot.player_a_overall_matches == 0
    assert snapshot.player_b_overall_matches == 0


def test_later_match_uses_only_prior_history() -> None:
    matches = [
        match(
            played_on=date(2025, 1, 1),
            winner="Alpha A.",
            loser="Zulu Z.",
            source_row=2,
        ),
        match(
            played_on=date(2025, 1, 2),
            winner="Zulu Z.",
            loser="Alpha A.",
            source_row=3,
        ),
    ]

    snapshot = TennisFeatureBuilder().build(matches)[1]

    assert snapshot.player_a == "Alpha A."
    assert snapshot.overall_elo_difference > 0
    assert snapshot.surface_elo_difference > 0
    assert snapshot.player_a_overall_matches == 1
    assert snapshot.player_b_overall_matches == 1
    assert snapshot.player_a_last_10_win_rate == 1.0
    assert snapshot.player_b_last_10_win_rate == 0.0
    assert snapshot.player_a_surface_last_10_win_rate == 1.0
    assert snapshot.player_b_surface_last_10_win_rate == 0.0
    assert snapshot.player_a_days_rest == 1
    assert snapshot.player_b_days_rest == 1
    assert snapshot.prior_h2h_matches == 1
    assert snapshot.player_a_h2h_win_rate is None


def test_matches_on_same_date_cannot_see_each_others_results() -> None:
    matches = [
        match(
            played_on=date(2025, 1, 1),
            winner="Alpha A.",
            loser="Zulu Z.",
            source_row=2,
        ),
        match(
            played_on=date(2025, 1, 1),
            winner="Zulu Z.",
            loser="Alpha A.",
            source_row=3,
        ),
    ]

    second_snapshot = TennisFeatureBuilder().build(matches)[1]

    assert second_snapshot.overall_elo_difference == 0.0
    assert second_snapshot.surface_elo_difference == 0.0
    assert second_snapshot.player_a_overall_matches == 0
    assert second_snapshot.player_b_overall_matches == 0
    assert second_snapshot.prior_h2h_matches == 0


def test_retirement_is_history_but_does_not_update_elo_or_form() -> None:
    matches = [
        match(
            played_on=date(2025, 1, 1),
            winner="Alpha A.",
            loser="Beta B.",
            source_row=2,
            status=TennisMatchStatus.RETIRED,
        ),
        match(
            played_on=date(2025, 1, 2),
            winner="Alpha A.",
            loser="Beta B.",
            source_row=3,
        ),
    ]

    snapshot = TennisFeatureBuilder().build(matches)[0]

    assert snapshot.overall_elo_difference == 0.0
    assert snapshot.player_a_overall_matches == 0
    assert snapshot.player_b_overall_matches == 0
    assert snapshot.player_a_recent_retirements == 0
    assert snapshot.player_b_recent_retirements == 1
    assert snapshot.player_a_days_rest == 1
    assert snapshot.player_b_days_rest == 1
