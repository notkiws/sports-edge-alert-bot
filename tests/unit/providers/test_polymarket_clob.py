from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from sports_edge.providers.polymarket_clob import PolymarketClobAdapter, PolymarketClobClient


def book_payload() -> dict[str, object]:
    return {
        "market": "condition-1",
        "asset_id": "player-token-1",
        "timestamp": "1788277279418",
        "bids": [
            {"price": "0.50", "size": "20"},
            {"price": "0.60", "size": "10"},
        ],
        "asks": [
            {"price": "0.75", "size": "20"},
            {"price": "0.70", "size": "5"},
            {"price": "0.72", "size": "3"},
        ],
        "min_order_size": "5",
        "tick_size": "0.01",
        "neg_risk": False,
    }


def test_normalizes_book_and_finds_true_best_prices() -> None:
    book = PolymarketClobAdapter().normalize_order_book(book_payload())

    assert book.token_id == "player-token-1"
    assert book.best_bid == Decimal("0.60")
    assert book.best_ask == Decimal("0.70")
    assert book.spread == Decimal("0.10")
    assert book.minimum_order_size == Decimal("5")


def test_effective_ask_uses_multiple_levels_in_best_price_order() -> None:
    book = PolymarketClobAdapter().normalize_order_book(book_payload())

    assert book.effective_ask_price(Decimal("10")) == Decimal("0.716")


def test_effective_ask_returns_none_when_depth_is_insufficient() -> None:
    payload = book_payload()
    payload["asks"] = [{"price": "0.70", "size": "5"}]
    book = PolymarketClobAdapter().normalize_order_book(payload)

    assert book.effective_ask_price(Decimal("6")) is None


def test_client_fetches_book_by_token_id() -> None:
    captured_urls: list[str] = []

    def transport(url: str) -> dict[str, object]:
        captured_urls.append(url)
        return book_payload()

    book = PolymarketClobClient(transport=transport).fetch_order_book("player-token-1")

    assert book.token_id == "player-token-1"
    query = parse_qs(urlparse(captured_urls[0]).query)
    assert query["token_id"] == ["player-token-1"]
