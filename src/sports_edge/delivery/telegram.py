"""Minimal Telegram Bot API transport with secret-safe errors."""

import fcntl
import json
import os
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sports_edge.reporting.telegram import render_daily_report
from sports_edge.scheduling.dry_run import DailyReportBatch


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram rejects or cannot complete a delivery."""


Transport = Callable[[str, Mapping[str, object]], Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class DeliverySummary:
    sent: int
    duplicates: int


def _default_transport(
    url: str,
    payload: Mapping[str, object],
) -> Mapping[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310
        result: object = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise TelegramDeliveryError("Telegram returned an invalid response")
    return result


class TelegramBotClient:
    """Send plain-text messages through one explicitly configured bot."""

    def __init__(
        self,
        token: str,
        *,
        transport: Transport = _default_transport,
        max_retries: int = 2,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not token:
            raise ValueError("Telegram token cannot be empty")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self._token = token
        self._transport = transport
        self._max_retries = max_retries
        self._sleep = sleep

    def send_message(self, *, chat_id: str, text: str) -> int:
        if not chat_id:
            raise ValueError("Telegram chat_id cannot be empty")
        if not text:
            raise ValueError("Telegram message cannot be empty")
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload: Mapping[str, object] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        response: Mapping[str, Any] | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport(url, payload)
                break
            except HTTPError as error:
                retryable = error.code == 429 or 500 <= error.code < 600
                if not retryable or attempt >= self._max_retries:
                    raise TelegramDeliveryError(
                        f"Telegram HTTP request failed with status {error.code}"
                    ) from None
            except URLError:
                if attempt >= self._max_retries:
                    raise TelegramDeliveryError("Telegram network request failed") from None
            self._sleep(float(2**attempt))
        if response is None:
            raise TelegramDeliveryError("Telegram request failed")
        if response.get("ok") is not True:
            description = str(response.get("description", "request rejected"))
            safe_description = description.replace(self._token, "[REDACTED]")
            raise TelegramDeliveryError(f"Telegram rejected message: {safe_description}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise TelegramDeliveryError("Telegram response did not contain a message ID")
        message_id = result.get("message_id")
        if not isinstance(message_id, int):
            raise TelegramDeliveryError("Telegram response did not contain a message ID")
        return message_id


def deliver_once(
    client: TelegramBotClient,
    *,
    chat_id: str,
    text: str,
    delivery_key: str,
    state_path: Path,
) -> int | None:
    """Deliver once per durable key and record only confirmed Telegram success."""

    if not delivery_key:
        raise ValueError("delivery_key cannot be empty")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("a+", encoding="utf-8") as state:
        fcntl.flock(state.fileno(), fcntl.LOCK_EX)
        state.seek(0)
        delivered_keys: set[str] = set()
        for line in state:
            if not line.strip():
                continue
            record: object = json.loads(line)
            if not isinstance(record, dict) or not isinstance(
                record.get("delivery_key"), str
            ):
                raise TelegramDeliveryError("Telegram delivery state is invalid")
            delivered_keys.add(record["delivery_key"])
        if delivery_key in delivered_keys:
            return None
        message_id = client.send_message(chat_id=chat_id, text=text)
        state.write(
            json.dumps(
                {"delivery_key": delivery_key, "message_id": message_id},
                sort_keys=True,
            )
            + "\n"
        )
        state.flush()
        os.fsync(state.fileno())
        return message_id


def deliver_due_batches(
    client: TelegramBotClient,
    *,
    chat_id: str,
    batches: Iterable[DailyReportBatch],
    now_utc: datetime,
    state_path: Path,
    polling_window: timedelta = timedelta(minutes=15),
) -> DeliverySummary:
    """Deliver due football selections while suppressing confirmed duplicates."""

    sent = 0
    duplicates = 0
    for batch in batches:
        if not (
            batch.scheduled_for_utc
            <= now_utc
            < batch.scheduled_for_utc + polling_window
        ):
            continue
        for selection in batch.selections:
            delivery_key = "|".join(
                (
                    "football",
                    selection.kickoff_utc.isoformat(),
                    selection.home_team,
                    selection.away_team,
                    selection.market,
                )
            )
            message_id = deliver_once(
                client,
                chat_id=chat_id,
                text=render_daily_report((selection,)),
                delivery_key=delivery_key,
                state_path=state_path,
            )
            if message_id is None:
                duplicates += 1
            else:
                sent += 1
    return DeliverySummary(sent=sent, duplicates=duplicates)
