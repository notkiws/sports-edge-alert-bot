"""Send due football reports through a disabled-by-default Telegram transport."""

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sports_edge.commands.render_telegram_dry_run import _load_selections
from sports_edge.delivery.telegram import TelegramBotClient, deliver_due_batches
from sports_edge.scheduling.dry_run import build_daily_batches


@dataclass(frozen=True, slots=True)
class SendCommandResult:
    enabled: bool
    sent: int
    duplicates: int


def send_due_reports(
    source: Path,
    state_path: Path,
    *,
    now_utc: datetime,
    environ: Mapping[str, str],
) -> SendCommandResult:
    """Send due reports only when the explicit environment gate is enabled."""

    enabled = environ.get("TELEGRAM_SENDING_ENABLED", "").casefold() == "true"
    if not enabled:
        return SendCommandResult(enabled=False, sent=0, duplicates=0)
    token = environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("Telegram credentials are incomplete")
    client = TelegramBotClient(token=token)
    summary = deliver_due_batches(
        client,
        chat_id=chat_id,
        batches=build_daily_batches(_load_selections(source)),
        now_utc=now_utc,
        state_path=state_path,
    )
    return SendCommandResult(
        enabled=True,
        sent=summary.sent,
        duplicates=summary.duplicates,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Send due football reports to Telegram.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/runtime/football-report-selections.json"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("artifacts/runtime/telegram-deliveries.jsonl"),
    )
    arguments = parser.parse_args()
    result = send_due_reports(
        arguments.input,
        arguments.state,
        now_utc=datetime.now(UTC),
        environ=os.environ,
    )
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == "__main__":
    main()
