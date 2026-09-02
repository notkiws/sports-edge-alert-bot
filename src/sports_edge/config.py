"""Runtime configuration for the frozen V1 strategy."""

from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class Settings:
    """Provider-independent strategy defaults."""

    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Jakarta"))
    football_probability_floor: float = 0.60
    tennis_probability_floor: float = 0.65
    polymarket_effective_price_ceiling: float = 0.7692
    regime_weight_candidates: tuple[float, ...] = (0.25, 0.50, 0.75)
    regime_weight_fallback: float = 0.50
    football_regime_pre_change_weight: float = 0.50
    football_enabled_markets: tuple[str, ...] = ("1X2", "TOTAL_2_5")
    football_disabled_markets: tuple[str, ...] = (
        "BTTS",
        "DOUBLE_CHANCE",
        "DRAW_NO_BET",
        "ASIAN_HANDICAP",
        "TEAM_TOTAL",
        "FIRST_HALF_RESULT",
        "FIRST_HALF_TOTAL",
    )
