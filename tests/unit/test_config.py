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
    assert settings.football_regime_pre_change_weight == 0.50
    assert settings.football_enabled_markets == ("1X2", "TOTAL_2_5")
    assert settings.football_disabled_markets == (
        "BTTS",
        "DOUBLE_CHANCE",
        "DRAW_NO_BET",
        "ASIAN_HANDICAP",
        "TEAM_TOTAL",
        "FIRST_HALF_RESULT",
        "FIRST_HALF_TOTAL",
    )
