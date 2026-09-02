import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sports_edge.backtests.tennis import (
    TennisMarketCandidate,
    qualify_tennis_candidate,
)
from sports_edge.domain.polymarket import (
    OrderBookLevel,
    PolymarketMarket,
    PolymarketOrderBook,
    PolymarketTennisEvent,
    PolymarketToken,
)
from sports_edge.domain.tennis import TennisTour
from sports_edge.storage.tennis_forward import append_tennis_snapshot


def event() -> PolymarketTennisEvent:
    return PolymarketTennisEvent(
        event_id="event-1",
        slug="djokovic-alcaraz",
        title="Novak Djokovic vs Carlos Alcaraz",
        tour=TennisTour.ATP,
        starts_at_utc=datetime(2026, 9, 10, 12, tzinfo=UTC),
        market=PolymarketMarket(
            market_id="market-1",
            condition_id="condition-1",
            question="Novak Djokovic vs Carlos Alcaraz",
            tokens=(
                PolymarketToken(token_id="token-djokovic", outcome="Novak Djokovic"),
                PolymarketToken(token_id="token-alcaraz", outcome="Carlos Alcaraz"),
            ),
        ),
    )


def order_book() -> PolymarketOrderBook:
    return PolymarketOrderBook(
        market_id="market-1",
        token_id="token-djokovic",
        timestamp_utc=datetime(2026, 9, 10, 9, 59, 30, tzinfo=UTC),
        bids=(OrderBookLevel(price=Decimal("0.59"), size=Decimal("100")),),
        asks=(OrderBookLevel(price=Decimal("0.60"), size=Decimal("100")),),
        minimum_order_size=Decimal("5"),
        tick_size=Decimal("0.01"),
    )


def candidate() -> TennisMarketCandidate:
    return TennisMarketCandidate(
        observed_at_utc=datetime(2026, 9, 10, 10, tzinfo=UTC),
        event=event(),
        selected_player="Novak Djokovic",
        selected_player_rank=1,
        model_probability=Decimal("0.70"),
        order_book=order_book(),
        target_size=Decimal("10"),
        fee_buffer=Decimal("0.005"),
        slippage_buffer=Decimal("0.005"),
        staleness_buffer=Decimal("0.005"),
        reliability_buffer=Decimal("0.005"),
        maximum_book_age=timedelta(minutes=1),
        maximum_spread=Decimal("0.05"),
        minimum_edge=Decimal("0.05"),
        first_match_after_long_absence=False,
    )


def test_exact_executable_positive_edge_candidate_qualifies() -> None:
    result = qualify_tennis_candidate(candidate())

    assert result.qualified
    assert result.rejection_reasons == ()
    assert result.token_id == "token-djokovic"
    assert result.executable_ask == Decimal("0.60")
    assert result.buffered_price == Decimal("0.620")
    assert result.edge == Decimal("0.080")


def test_wide_order_book_is_rejected() -> None:
    wide_book = replace(
        order_book(),
        asks=(OrderBookLevel(price=Decimal("0.70"), size=Decimal("100")),),
    )

    result = qualify_tennis_candidate(replace(candidate(), order_book=wide_book))

    assert not result.qualified
    assert "SPREAD_TOO_WIDE" in result.rejection_reasons


def test_observation_at_match_start_is_rejected() -> None:
    started = replace(candidate(), observed_at_utc=event().starts_at_utc)

    result = qualify_tennis_candidate(started)

    assert not result.qualified
    assert "EVENT_ALREADY_STARTED" in result.rejection_reasons


def test_target_below_minimum_order_size_is_rejected() -> None:
    result = qualify_tennis_candidate(
        replace(candidate(), target_size=Decimal("2"))
    )

    assert not result.qualified
    assert "TARGET_BELOW_MINIMUM_ORDER_SIZE" in result.rejection_reasons


def test_unfrozen_edge_threshold_is_rejected() -> None:
    result = qualify_tennis_candidate(replace(candidate(), minimum_edge=None))

    assert not result.qualified
    assert "EDGE_THRESHOLD_UNFROZEN" in result.rejection_reasons


def test_forward_snapshot_store_is_append_only_and_idempotent(tmp_path: Path) -> None:
    market_candidate = candidate()
    result = qualify_tennis_candidate(market_candidate)
    destination = tmp_path / "tennis-forward.jsonl"

    assert append_tennis_snapshot(destination, market_candidate, result)
    assert not append_tennis_snapshot(destination, market_candidate, result)

    rows = [json.loads(line) for line in destination.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["event_id"] == "event-1"
    assert rows[0]["token_id"] == "token-djokovic"
    assert rows[0]["target_size"] == "10"
    assert rows[0]["qualified"] is True
