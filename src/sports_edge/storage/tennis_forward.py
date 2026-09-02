"""Append-only storage for forward Polymarket tennis observations."""

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from sports_edge.backtests.tennis import (
    TennisMarketCandidate,
    TennisQualificationResult,
)
from sports_edge.domain.polymarket import PolymarketOrderBook, PolymarketTennisEvent


def _snapshot_id(candidate: TennisMarketCandidate, token_id: str | None) -> str:
    return ":".join(
        (
            candidate.event.event_id,
            token_id or "unmatched",
            candidate.order_book.timestamp_utc.isoformat(),
        )
    )


def _decimal(value: object) -> str | None:
    return None if value is None else str(value)


def _record(
    candidate: TennisMarketCandidate,
    result: TennisQualificationResult,
) -> dict[str, object]:
    book = candidate.order_book
    return {
        "snapshot_id": _snapshot_id(candidate, result.token_id),
        "observed_at_utc": candidate.observed_at_utc.isoformat(),
        "event_id": candidate.event.event_id,
        "event_slug": candidate.event.slug,
        "event_title": candidate.event.title,
        "event_starts_at_utc": candidate.event.starts_at_utc.isoformat(),
        "tour": candidate.event.tour.value,
        "market_id": candidate.event.market.market_id,
        "condition_id": candidate.event.market.condition_id,
        "selected_player": candidate.selected_player,
        "selected_player_rank": candidate.selected_player_rank,
        "model_probability": str(candidate.model_probability),
        "token_id": result.token_id,
        "book_timestamp_utc": book.timestamp_utc.isoformat(),
        "best_bid": _decimal(book.best_bid),
        "best_ask": _decimal(book.best_ask),
        "spread": _decimal(book.spread),
        "bids": [
            {"price": str(level.price), "size": str(level.size)} for level in book.bids
        ],
        "asks": [
            {"price": str(level.price), "size": str(level.size)} for level in book.asks
        ],
        "minimum_order_size": str(book.minimum_order_size),
        "target_size": str(candidate.target_size),
        "executable_ask": _decimal(result.executable_ask),
        "fee_buffer": str(candidate.fee_buffer),
        "slippage_buffer": str(candidate.slippage_buffer),
        "staleness_buffer": str(candidate.staleness_buffer),
        "reliability_buffer": str(candidate.reliability_buffer),
        "buffered_price": _decimal(result.buffered_price),
        "effective_price_ceiling": str(candidate.effective_price_ceiling),
        "minimum_edge": _decimal(candidate.minimum_edge),
        "edge": _decimal(result.edge),
        "qualified": result.qualified,
        "rejection_reasons": list(result.rejection_reasons),
    }


def _append_record(path: Path, record: dict[str, object]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_id = record["snapshot_id"]
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            existing_ids = {
                parsed.get("snapshot_id")
                for line in handle
                if line.strip()
                for parsed in (json.loads(line),)
            }
            if snapshot_id in existing_ids:
                return False
            handle.seek(0, os.SEEK_END)
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_tennis_snapshot(
    path: Path,
    candidate: TennisMarketCandidate,
    result: TennisQualificationResult,
) -> bool:
    """Append one model-evaluated observation unless it already exists."""

    return _append_record(path, _record(candidate, result))


def append_polymarket_book_snapshot(
    path: Path,
    event: PolymarketTennisEvent,
    book: PolymarketOrderBook,
    observed_at_utc: datetime,
) -> bool:
    """Append a read-only market observation before model evaluation."""

    record: dict[str, object] = {
        "snapshot_id": ":".join(
            (event.event_id, book.token_id, book.timestamp_utc.isoformat())
        ),
        "observed_at_utc": observed_at_utc.isoformat(),
        "event_id": event.event_id,
        "event_slug": event.slug,
        "event_title": event.title,
        "event_starts_at_utc": event.starts_at_utc.isoformat(),
        "tour": event.tour.value,
        "market_id": event.market.market_id,
        "condition_id": event.market.condition_id,
        "token_id": book.token_id,
        "book_timestamp_utc": book.timestamp_utc.isoformat(),
        "best_bid": _decimal(book.best_bid),
        "best_ask": _decimal(book.best_ask),
        "spread": _decimal(book.spread),
        "bids": [
            {"price": str(level.price), "size": str(level.size)} for level in book.bids
        ],
        "asks": [
            {"price": str(level.price), "size": str(level.size)} for level in book.asks
        ],
        "minimum_order_size": str(book.minimum_order_size),
        "qualified": False,
        "rejection_reasons": ["MODEL_NOT_EVALUATED"],
    }
    return _append_record(path, record)
