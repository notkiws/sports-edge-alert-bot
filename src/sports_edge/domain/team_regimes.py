"""Point-in-time team regime changes and historical sample weighting."""

from dataclasses import dataclass
from datetime import datetime, timedelta


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class TeamRegimeChange:
    """A source-dated manager or regular-player structural change."""

    team_id: str
    effective_at_utc: datetime
    recorded_at_utc: datetime
    manager_changed: bool
    regular_starters_changed: int | None
    reason: str
    source_url: str

    def __post_init__(self) -> None:
        _require_utc(self.effective_at_utc, "effective_at_utc")
        _require_utc(self.recorded_at_utc, "recorded_at_utc")

    @property
    def starts_new_regime(self) -> bool:
        return self.manager_changed or (
            self.regular_starters_changed is not None and self.regular_starters_changed >= 6
        )

    def is_known_at(self, prediction_at_utc: datetime) -> bool:
        _require_utc(prediction_at_utc, "prediction_at_utc")
        return (
            self.starts_new_regime
            and self.effective_at_utc <= prediction_at_utc
            and self.recorded_at_utc <= prediction_at_utc
        )


def team_sample_weight(
    sample_at_utc: datetime,
    prediction_at_utc: datetime,
    change: TeamRegimeChange,
    *,
    pre_change_weight: float,
) -> float:
    """Return a changed team's point-in-time weight for one historical sample."""

    _require_utc(sample_at_utc, "sample_at_utc")
    _require_utc(prediction_at_utc, "prediction_at_utc")
    if not 0.0 <= pre_change_weight <= 1.0:
        raise ValueError("pre_change_weight must be between 0 and 1")
    if not change.is_known_at(prediction_at_utc):
        return 1.0
    if sample_at_utc < change.effective_at_utc:
        return pre_change_weight
    return 1.0
