# Sports Probability Alert Bot — V1 Architecture

## 1. Design goals

- $0/month data path for private/personal V1.
- Football probability forecasts without odds/value claims.
- Independent tennis model compared with executable Polymarket CLOB asks.
- Provider-independent canonical models and immutable raw snapshots.
- Leakage-safe chronological backtests.
- UTC storage, UTC+7 reports.
- No bet placement, bookmaker credentials, stakes, or accumulators.

## 2. Stack

- Python 3.11+
- Pydantic v2 and HTTPX
- Polars + DuckDB + Parquet for historical data/backtests
- SQLite for runtime state
- scipy/statsmodels/scikit-learn for modeling/calibration
- APScheduler and python-telegram-bot
- pytest, Hypothesis, Ruff, mypy

## 3. Data flow

```text
football-data.org API              Tennis-Data files
          │                               │
          ▼                               ▼
 football raw snapshots          tennis historical lake
          │                               │
          ▼                               ▼
 football normalizer             tennis feature/model pipeline
          │                               │
          ▼                               │
 football feature/model pipeline          │
          │                               │
          ▼                               │
 probability forecasts           Polymarket Gamma discovery
          │                               │
          │                      strict event/contract matcher
          │                               │
          │                       CLOB order-book snapshot
          │                               │
          │                       executable ask/VWAP + edge
          │                               │
          └──────────────┬────────────────┘
                         ▼
            qualification and ranking
                         │
                         ▼
             bilingual daily renderer
                         │
                         ▼
                    Telegram
```

## 4. Provider interfaces

### `FootballDataProvider`

```text
list_competitions()
list_events(date_range, competition_ids)
get_event(event_id)
get_standings(competition_id, season)
get_matches(competition_id, season/date_range)
```

The adapter must persist raw responses, honor 10-calls/minute free-tier limits, cache aggressively, and disable unavailable competitions rather than substituting scraped data.

### `TennisHistoricalProvider`

```text
list_files(year, tour)
load_matches(year, tour)
normalize_match(record)
```

The adapter downloads/caches Tennis-Data files, records source URL/hash/retrieval timestamp/schema, and rejects schema drift. Historical source files must not be redistributed.

### `PolymarketProvider`

```text
discover_events(time_range, sport="tennis")
get_markets(event_id)
get_order_book(token_id)
get_price_history(token_id, interval)
executable_ask_vwap(token_id, target_size)
```

Use Gamma for discovery and CLOB `/book` as the price authority. No wallet/trading authentication belongs in the repository.

## 5. Canonical entities

- `Competition`
- `Tournament`
- `Event`
- `Participant`
- `RankingSnapshot`
- `FootballMatchResult`
- `TennisMatchResult`
- `MarketDefinition`
- `PolymarketContract`
- `OrderBookSnapshot`
- `FeatureSnapshot`
- `ModelArtifact`
- `Prediction`
- `FootballForecastOption`
- `TennisEdgeSelection`
- `DailyReport`
- `AlertRevision`

Every time-dependent row includes `observed_at_utc`, `effective_at_utc`, source ID, and raw snapshot reference.

## 6. Football pipeline

### Features

At historical cutoff `as_of_utc`, derive only prior data:

- last 10 matches;
- goals for/against;
- home/away splits;
- opponent-adjusted strength;
- league-table/form context;
- H2H from previous three seasons;
- full-time/half-time distributions;
- rest/congestion when derivable;
- missingness/data-quality flags.

### Models

- Poisson/Dixon-Coles baseline;
- regularized tabular model;
- calibrated ensemble.

Models emit a coherent score distribution from which canonical option probabilities are derived. Derived probabilities must respect logical invariants; for example, probabilities of mutually exclusive 1X2 outcomes sum to one.

### Qualifier

For each match:

- compute all supported option probabilities;
- remove redundant duplicates;
- require each displayed option to be at least 0.60;
- rank by probability, confidence, agreement, and data quality;
- return at most three;
- return no match section when none qualify.

No football odds/edge fields exist in the V1 domain or renderer.

## 7. Tennis pipeline

### Historical features

From Tennis-Data records, point-in-time only:

- latest reliable ranking-at-tournament;
- top-50 eligibility;
- surface-aware Elo;
- last 10 overall;
- last 10 current-surface matches;
- opponent strength;
- H2H after three prior meetings;
- prior retirement/walkover flags;
- rest/fatigue when derivable;
- tournament level and format.

### Model

Train a calibrated ranking/surface/form classifier. Model artifacts include data hashes, cutoff, schema, calibration, feature definitions, and segment/pooled-fallback metadata.

### Current event matching

A strict matcher maps a Polymarket match-winner contract to model participants. Require:

- normalized player identities;
- exact individual match, not outright;
- compatible tournament and date/round window;
- correct outcome orientation;
- compatible cancellation/retirement settlement rules.

Ambiguity means rejection, never heuristic auto-acceptance.

### Executable price and edge

Read the CLOB order book and calculate the best ask or target-size VWAP. Record:

- token ID;
- observed/received timestamps;
- price levels and available sizes;
- spread;
- target-size VWAP;
- configured fee/slippage/staleness buffer.

```text
effective_market_probability = ask_vwap + fee_buffer + slippage_buffer + staleness_buffer
edge = model_probability - effective_market_probability
```

Qualify only when all `STRATEGY.md` tennis rules pass, including model probability ≥0.65, top-50 eligibility, effective price ≤0.7692, validated minimum edge, freshness/depth, and unambiguous mapping.

## 8. Backtests

### Football

- Two completed seasons where free API coverage is reliable.
- Chronological train/validation/holdout.
- Evaluate hit rate, confidence interval, Brier score, calibration curves, sample, and segment stability.
- Never report ROI or edge without odds.

### Tennis

- Two completed years of Tennis-Data where schemas/coverage pass validation.
- Chronological train/validation/holdout.
- Historical closing odds can support provisional value analysis but are not equivalent to production CLOB asks.
- Persist all production Polymarket order books to build a true forward decision-time dataset.

## 9. Runtime scheduler

- Discover UTC+7 day events.
- Determine the earliest covered event.
- Build and send one report three hours before it.
- Persist report idempotency key by UTC+7 date.
- Continue monitoring only for cancellation/withdrawal/material data corrections.
- Never send updates for price movement alone unless the tennis selection changes qualification status.

## 10. Alert state

```text
UNSEEN -> QUALIFIED -> ALERTED -> STILL_VALID
                         |             |
                         └─────────────┴──> EXPIRED_OR_CANCELLED
UNSEEN/REJECTED -> QUALIFIED_AFTER_REPORT -> NEW update
```

Football and tennis reasons remain separate:

Football rejection examples:

- `PROBABILITY_BELOW_60`
- `INSUFFICIENT_HISTORY`
- `UNCALIBRATED_SEGMENT`
- `LOW_DATA_QUALITY`

Tennis rejection examples:

- `MODEL_PROBABILITY_BELOW_65`
- `PLAYER_OUTSIDE_TOP_50`
- `STALE_RANKING`
- `AMBIGUOUS_CONTRACT`
- `STALE_OR_EMPTY_BOOK`
- `EFFECTIVE_PRICE_ABOVE_07692`
- `EDGE_BELOW_THRESHOLD`
- `FIRST_MATCH_AFTER_ABSENCE`

## 11. Storage and auditing

- Immutable raw football JSON snapshots.
- Immutable source metadata and hashes for Tennis-Data files.
- Immutable Polymarket order-book snapshots.
- Canonical entity mappings with manual override support.
- Frozen model/config/data hashes.
- Explainable pass/fail reason for every evaluated option/contract.
- No licensed/open source raw dataset redistribution.

## 12. Security and operations

- football-data.org API key and Telegram token only in local environment/service secret files.
- No Polymarket wallet key.
- Logs redact tokens and query-string keys.
- Cache provider responses to remain within free quotas.
- Fail closed on stale data, mapping ambiguity, missing order books, or quota exhaustion.
- Personal/private Telegram chat only in V1.

## 13. Proof gates

Before enabling alerts:

1. Free football-data.org key confirms each enabled competition and two-season history.
2. Football half-time/deep fields are measured; unsupported markets are disabled.
3. Tennis-Data 2024–2026 files download successfully, schemas are mapped, and private-use terms are accepted.
4. Target ATP/WTA 500+ events can be reliably classified.
5. Polymarket individual match contracts can be distinguished from outrights.
6. CLOB book-side semantics and ask VWAP are covered by recorded contract tests.
7. Local network restrictions are not bypassed; deployment has lawful direct read access.
8. Football calibration and tennis historical edge gates pass with real outputs.
9. One end-to-end dry report is rendered before Telegram sending is enabled.
