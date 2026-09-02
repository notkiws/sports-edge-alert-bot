"""Tennis executable-price qualification and forward validation entities."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from unicodedata import category, normalize

from sports_edge.domain.polymarket import (
    PolymarketOrderBook,
    PolymarketTennisEvent,
)


@dataclass(frozen=True, slots=True)
class TennisMarketCandidate:
    observed_at_utc: datetime
    event: PolymarketTennisEvent
    selected_player: str
    selected_player_rank: int | None
    model_probability: Decimal
    order_book: PolymarketOrderBook
    target_size: Decimal
    fee_buffer: Decimal
    slippage_buffer: Decimal
    staleness_buffer: Decimal
    reliability_buffer: Decimal
    maximum_book_age: timedelta
    maximum_spread: Decimal
    minimum_edge: Decimal | None
    first_match_after_long_absence: bool
    probability_floor: Decimal = Decimal("0.65")
    effective_price_ceiling: Decimal = Decimal("0.7692")


@dataclass(frozen=True, slots=True)
class TennisQualificationResult:
    qualified: bool
    rejection_reasons: tuple[str, ...]
    token_id: str | None
    executable_ask: Decimal | None
    buffered_price: Decimal | None
    edge: Decimal | None


def normalize_player_name(value: str) -> str:
    """Normalize a full player name without fuzzy or initials-based matching."""

    decomposed = normalize("NFKD", value)
    characters = [
        character.casefold()
        if character.isalnum()
        else " "
        for character in decomposed
        if category(character) != "Mn"
    ]
    return " ".join("".join(characters).split())


def qualify_tennis_candidate(
    candidate: TennisMarketCandidate,
) -> TennisQualificationResult:
    """Evaluate one exact match-winner token at an executable target size."""

    selected_name = normalize_player_name(candidate.selected_player)
    matching_tokens = tuple(
        token
        for token in candidate.event.market.tokens
        if normalize_player_name(token.outcome) == selected_name
    )
    if len(matching_tokens) != 1:
        return TennisQualificationResult(
            qualified=False,
            rejection_reasons=("AMBIGUOUS_PLAYER_TOKEN",),
            token_id=None,
            executable_ask=None,
            buffered_price=None,
            edge=None,
        )
    token = matching_tokens[0]
    if (
        candidate.order_book.market_id != candidate.event.market.market_id
        or candidate.order_book.token_id != token.token_id
    ):
        return TennisQualificationResult(
            qualified=False,
            rejection_reasons=("ORDER_BOOK_TOKEN_MISMATCH",),
            token_id=token.token_id,
            executable_ask=None,
            buffered_price=None,
            edge=None,
        )
    executable_ask = candidate.order_book.effective_ask_price(candidate.target_size)
    if executable_ask is None:
        return TennisQualificationResult(
            qualified=False,
            rejection_reasons=("INSUFFICIENT_ASK_DEPTH",),
            token_id=token.token_id,
            executable_ask=None,
            buffered_price=None,
            edge=None,
        )
    buffered_price = executable_ask + sum(
        (
            candidate.fee_buffer,
            candidate.slippage_buffer,
            candidate.staleness_buffer,
            candidate.reliability_buffer,
        ),
        Decimal(0),
    )
    edge = candidate.model_probability - buffered_price
    reasons: list[str] = []
    if candidate.observed_at_utc >= candidate.event.starts_at_utc:
        reasons.append("EVENT_ALREADY_STARTED")
    if candidate.target_size < candidate.order_book.minimum_order_size:
        reasons.append("TARGET_BELOW_MINIMUM_ORDER_SIZE")
    book_age = candidate.observed_at_utc - candidate.order_book.timestamp_utc
    if book_age < timedelta(0) or book_age > candidate.maximum_book_age:
        reasons.append("STALE_ORDER_BOOK")
    spread = candidate.order_book.spread
    if spread is None:
        reasons.append("UNAVAILABLE_SPREAD")
    elif spread > candidate.maximum_spread:
        reasons.append("SPREAD_TOO_WIDE")
    if candidate.model_probability < candidate.probability_floor:
        reasons.append("MODEL_PROBABILITY_BELOW_FLOOR")
    if candidate.selected_player_rank is None or not 1 <= candidate.selected_player_rank <= 50:
        reasons.append("PLAYER_RANK_OUT_OF_SCOPE")
    if candidate.first_match_after_long_absence:
        reasons.append("FIRST_MATCH_AFTER_LONG_ABSENCE")
    if buffered_price > candidate.effective_price_ceiling:
        reasons.append("EFFECTIVE_PRICE_ABOVE_CEILING")
    if candidate.minimum_edge is None:
        reasons.append("EDGE_THRESHOLD_UNFROZEN")
    elif edge < candidate.minimum_edge:
        reasons.append("EDGE_BELOW_MINIMUM")
    return TennisQualificationResult(
        qualified=not reasons,
        rejection_reasons=tuple(reasons),
        token_id=token.token_id,
        executable_ask=executable_ask,
        buffered_price=buffered_price,
        edge=edge,
    )
