import json
from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook

from sports_edge.domain.tennis import (
    TennisMatchStatus,
    TennisTour,
    TournamentLevel,
)
from sports_edge.providers.tennis_data import TennisDataWorkbookReader, write_matches_jsonl

HEADERS = [
    "Location",
    "Tournament",
    "Date",
    "Level",
    "Court",
    "Surface",
    "Round",
    "Winner",
    "Loser",
    "WRank",
    "LRank",
    "Comment",
]


def write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def row(level: str, *, round_name: str = "1st Round", comment: str = "Completed") -> list[object]:
    return [
        "London",
        "Example Open",
        datetime(2025, 6, 1),
        level,
        "Outdoor",
        "Grass",
        round_name,
        "Winner A.",
        "Loser B.",
        12,
        48,
        comment,
    ]


def test_atp_reader_keeps_only_eligible_tiers(tmp_path: Path) -> None:
    path = tmp_path / "atp.xlsx"
    write_workbook(path, [row("ATP250"), row("ATP500"), row("Masters 1000"), row("Masters Cup")])

    matches = TennisDataWorkbookReader().read(path, TennisTour.ATP)

    assert [match.level for match in matches] == [
        TournamentLevel.LEVEL_500,
        TournamentLevel.LEVEL_1000,
        TournamentLevel.FINALS,
    ]
    assert matches[0].played_on == date(2025, 6, 1)
    assert matches[0].winner_rank == 12
    assert matches[0].loser_rank == 48


def test_wta_reader_keeps_500_1000_finals_and_slams(tmp_path: Path) -> None:
    path = tmp_path / "wta.xlsx"
    write_workbook(
        path,
        [
            row("WTA250"),
            row("WTA500"),
            row("WTA1000"),
            row("Tour Championships"),
            row("Grand Slam"),
        ],
    )

    matches = TennisDataWorkbookReader().read(path, TennisTour.WTA)

    assert [match.level for match in matches] == [
        TournamentLevel.LEVEL_500,
        TournamentLevel.LEVEL_1000,
        TournamentLevel.FINALS,
        TournamentLevel.GRAND_SLAM,
    ]


def test_reader_excludes_qualifying_and_preserves_retirement(tmp_path: Path) -> None:
    path = tmp_path / "atp.xlsx"
    write_workbook(
        path,
        [
            row("ATP500", round_name="Qualification"),
            row("ATP500", comment="Retired"),
        ],
    )

    matches = TennisDataWorkbookReader().read(path, TennisTour.ATP)

    assert len(matches) == 1
    assert matches[0].status is TennisMatchStatus.RETIRED
    assert matches[0].source_row == 3


def test_writes_normalized_jsonl_with_provenance(tmp_path: Path) -> None:
    workbook = tmp_path / "atp.xlsx"
    write_workbook(workbook, [row("ATP500")])
    matches = TennisDataWorkbookReader().read(workbook, TennisTour.ATP)

    destination = write_matches_jsonl(matches, tmp_path / "normalized" / "matches.jsonl")

    records = [json.loads(line) for line in destination.read_text().splitlines()]
    assert records[0]["source"] == "tennis-data.co.uk"
    assert records[0]["source_file"] == "atp.xlsx"
    assert records[0]["source_row"] == 2
    assert records[0]["played_on"] == "2025-06-01"
    assert records[0]["tour"] == "ATP"
    assert records[0]["level"] == "500"
