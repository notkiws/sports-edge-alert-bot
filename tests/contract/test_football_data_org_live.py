import os

import pytest

from sports_edge.providers.football_data_org_client import FootballDataOrgClient


def test_live_free_account_returns_premier_league_season() -> None:
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        pytest.skip("FOOTBALL_DATA_API_KEY is not set")

    payload = FootballDataOrgClient(api_key).fetch_competition_matches("PL", 2025)

    matches = payload.get("matches")
    assert isinstance(matches, list)
    assert len(matches) == 380
    assert all(match.get("competition", {}).get("code") == "PL" for match in matches)
