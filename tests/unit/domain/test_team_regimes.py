from datetime import UTC, datetime

from sports_edge.domain.team_regimes import TeamRegimeChange, team_sample_weight


def at(day: int) -> datetime:
    return datetime(2026, 8, day, tzinfo=UTC)


def test_manager_change_starts_new_regime() -> None:
    change = TeamRegimeChange(
        team_id="61",
        effective_at_utc=at(10),
        recorded_at_utc=at(10),
        manager_changed=True,
        regular_starters_changed=0,
        reason="New manager appointed",
        source_url="https://example.test/source",
    )

    assert change.starts_new_regime


def test_six_changed_regular_starters_starts_new_regime() -> None:
    assert TeamRegimeChange(
        team_id="61",
        effective_at_utc=at(10),
        recorded_at_utc=at(10),
        manager_changed=False,
        regular_starters_changed=6,
        reason="Majority turnover",
        source_url="https://example.test/source",
    ).starts_new_regime


def test_five_changed_regular_starters_does_not_start_new_regime() -> None:
    assert not TeamRegimeChange(
        team_id="61",
        effective_at_utc=at(10),
        recorded_at_utc=at(10),
        manager_changed=False,
        regular_starters_changed=5,
        reason="Minority turnover",
        source_url="https://example.test/source",
    ).starts_new_regime


def test_change_recorded_after_prediction_is_not_visible() -> None:
    change = TeamRegimeChange(
        team_id="61",
        effective_at_utc=at(10),
        recorded_at_utc=at(20),
        manager_changed=True,
        regular_starters_changed=0,
        reason="Late historical record",
        source_url="https://example.test/source",
    )

    assert not change.is_known_at(at(15))
    assert team_sample_weight(at(5), at(15), change, pre_change_weight=0.5) == 1.0


def test_known_change_downweights_only_pre_change_samples() -> None:
    change = TeamRegimeChange(
        team_id="61",
        effective_at_utc=at(10),
        recorded_at_utc=at(10),
        manager_changed=True,
        regular_starters_changed=0,
        reason="New manager appointed",
        source_url="https://example.test/source",
    )

    assert team_sample_weight(at(5), at(20), change, pre_change_weight=0.5) == 0.5
    assert team_sample_weight(at(12), at(20), change, pre_change_weight=0.5) == 1.0
