from datetime import UTC, datetime
from pathlib import Path

import pytest

from sports_edge.commands.send_telegram_due import send_due_reports


def test_sending_is_disabled_by_default_before_loading_input(tmp_path: Path) -> None:
    result = send_due_reports(
        tmp_path / "missing.json",
        tmp_path / "state.jsonl",
        now_utc=datetime(2026, 9, 5, 11, tzinfo=UTC),
        environ={},
    )

    assert result.enabled is False
    assert result.sent == 0
    assert result.duplicates == 0


def test_enabled_sending_requires_private_credentials(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="credentials are incomplete"):
        send_due_reports(
            tmp_path / "missing.json",
            tmp_path / "state.jsonl",
            now_utc=datetime(2026, 9, 5, 11, tzinfo=UTC),
            environ={"TELEGRAM_SENDING_ENABLED": "true"},
        )
