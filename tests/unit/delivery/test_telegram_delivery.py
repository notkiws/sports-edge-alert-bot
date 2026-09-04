from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError

import pytest

from sports_edge.delivery.telegram import (
    TelegramBotClient,
    TelegramDeliveryError,
    deliver_due_batches,
    deliver_once,
)
from sports_edge.reporting.telegram import FootballReportSelection
from sports_edge.scheduling.dry_run import build_daily_batches


class FakeTransport:
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    def __call__(
        self,
        url: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, Any]:
        self.calls.append((url, payload))
        return self.response


def test_send_message_posts_plain_text_to_configured_chat() -> None:
    transport = FakeTransport({"ok": True, "result": {"message_id": 42}})
    client = TelegramBotClient(token="fake-token", transport=transport)

    message_id = client.send_message(chat_id="-100123", text="hello")

    assert message_id == 42
    url, payload = transport.calls[0]
    assert url == "https://api.telegram.org/botfake-token/sendMessage"
    assert payload == {
        "chat_id": "-100123",
        "text": "hello",
        "disable_web_page_preview": True,
    }


def test_delivery_error_does_not_expose_token() -> None:
    transport = FakeTransport({"ok": False, "description": "Bad Request"})
    client = TelegramBotClient(token="never-print-token", transport=transport)

    with pytest.raises(TelegramDeliveryError) as error:
        client.send_message(chat_id="123", text="hello")

    assert "never-print-token" not in str(error.value)
    assert "Bad Request" in str(error.value)


def test_network_failure_retries_twice_then_succeeds() -> None:
    attempts = 0
    waits: list[float] = []

    def transport(url: str, payload: Mapping[str, object]) -> Mapping[str, Any]:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise URLError("temporary")
        return {"ok": True, "result": {"message_id": 7}}

    client = TelegramBotClient(
        token="fake-token",
        transport=transport,
        max_retries=2,
        sleep=waits.append,
    )

    assert client.send_message(chat_id="123", text="hello") == 7
    assert attempts == 3
    assert waits == [1.0, 2.0]


def test_deliver_once_records_success_and_skips_duplicate(tmp_path: Path) -> None:
    transport = FakeTransport({"ok": True, "result": {"message_id": 42}})
    client = TelegramBotClient(token="fake-token", transport=transport)
    state_path = tmp_path / "telegram-deliveries.jsonl"

    first = deliver_once(
        client,
        chat_id="123",
        text="daily report",
        delivery_key="football:2026-09-05",
        state_path=state_path,
    )
    second = deliver_once(
        client,
        chat_id="123",
        text="daily report",
        delivery_key="football:2026-09-05",
        state_path=state_path,
    )

    assert first == 42
    assert second is None
    assert len(transport.calls) == 1
    assert "football:2026-09-05" in state_path.read_text()


def test_deliver_due_batches_sends_each_selection_once(tmp_path: Path) -> None:
    selection = FootballReportSelection(
        competition="Premier League",
        kickoff_utc=datetime(2026, 9, 5, 14, tzinfo=UTC),
        home_team="Manchester City FC",
        away_team="Coventry City FC",
        market="1X2",
        selection_en="HOME",
        selection_id="TUAN RUMAH",
        probability=0.761,
        historical_hit_rate=0.713,
        historical_sample_size=296,
        grade="C",
        reasoning_en=(
            "Limited prior-match history "
            "(Manchester City FC: 76, Coventry City FC: 0)."
        ),
        reasoning_id=(
            "Riwayat pertandingan sebelumnya terbatas "
            "(Manchester City FC: 76, Coventry City FC: 0)."
        ),
        warning_en="",
        warning_id="",
    )
    batches = build_daily_batches((selection,))
    transport = FakeTransport({"ok": True, "result": {"message_id": 42}})
    client = TelegramBotClient(token="fake-token", transport=transport)
    state_path = tmp_path / "telegram-deliveries.jsonl"

    first = deliver_due_batches(
        client,
        chat_id="123",
        batches=batches,
        now_utc=datetime(2026, 9, 5, 11, tzinfo=UTC),
        state_path=state_path,
    )
    second = deliver_due_batches(
        client,
        chat_id="123",
        batches=batches,
        now_utc=datetime(2026, 9, 5, 11, 5, tzinfo=UTC),
        state_path=state_path,
    )

    assert first.sent == 1
    assert first.duplicates == 0
    assert second.sent == 0
    assert second.duplicates == 1
    assert len(transport.calls) == 1
    assert "Reason / Alasan:" in str(transport.calls[0][1]["text"])
