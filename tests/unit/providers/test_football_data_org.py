from copy import deepcopy
from datetime import UTC, datetime

import pytest

from sports_edge.domain.football import MatchStatus
from sports_edge.providers.football_data_org import (
    FootballDataOrgAdapter,
    UnsupportedCompetition,
)


def finished_payload() -> dict[str, object]:
    return {
        "id": 54321,
        "utcDate": "2026-09-02T18:30:00Z",
        "status": "FINISHED",
        "competition": {"id": 2021, "code": "PL", "name": "Premier League"},
        "homeTeam": {"id": 61, "name": "Chelsea FC"},
        "awayTeam": {"id": 64, "name": "Liverpool FC"},
        "score": {
            "fullTime": {"home": 2, "away": 1},
            "halfTime": {"home": 1, "away": 0},
        },
    }


def test_normalizes_finished_match_without_losing_scores() -> None:
    match = FootballDataOrgAdapter().normalize_match(finished_payload())

    assert match.source == "football-data.org"
    assert match.source_id == "54321"
    assert match.competition.code == "PL"
    assert match.kickoff_utc == datetime(2026, 9, 2, 18, 30, tzinfo=UTC)
    assert match.status is MatchStatus.FINISHED
    assert match.score.full_time == (2, 1)
    assert match.score.half_time == (1, 0)
    assert match.quality_flags == frozenset()


def test_finished_match_marks_missing_half_time_without_inventing_it() -> None:
    payload = deepcopy(finished_payload())
    payload["score"]["halfTime"] = {"home": None, "away": None}  # type: ignore[index]

    match = FootballDataOrgAdapter().normalize_match(payload)

    assert match.score.half_time is None
    assert match.quality_flags == frozenset({"MISSING_HALF_TIME_SCORE"})


def test_scheduled_match_allows_scores_to_be_absent() -> None:
    payload = deepcopy(finished_payload())
    payload["status"] = "SCHEDULED"
    payload["score"] = {
        "fullTime": {"home": None, "away": None},
        "halfTime": {"home": None, "away": None},
    }

    match = FootballDataOrgAdapter().normalize_match(payload)

    assert match.status is MatchStatus.SCHEDULED
    assert match.score.full_time is None
    assert match.score.half_time is None
    assert match.quality_flags == frozenset()


def test_rejects_competition_outside_verified_free_allowlist() -> None:
    payload = deepcopy(finished_payload())
    payload["competition"]["code"] = "EL"  # type: ignore[index]
    payload["competition"]["name"] = "UEFA Europa League"  # type: ignore[index]

    with pytest.raises(UnsupportedCompetition, match="EL"):
        FootballDataOrgAdapter().normalize_match(payload)
