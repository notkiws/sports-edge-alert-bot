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
