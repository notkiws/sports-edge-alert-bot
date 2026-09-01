from zoneinfo import ZoneInfo

from sports_edge.config import Settings


def test_strategy_defaults_match_frozen_v1() -> None:
    settings = Settings()

    assert settings.timezone == ZoneInfo("Asia/Jakarta")
    assert settings.football_probability_floor == 0.60
    assert settings.tennis_probability_floor == 0.65
    assert settings.polymarket_effective_price_ceiling == 0.7692
    assert settings.regime_weight_candidates == (0.25, 0.50, 0.75)
    assert settings.regime_weight_fallback == 0.50
