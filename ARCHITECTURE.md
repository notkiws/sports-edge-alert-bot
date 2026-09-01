# Sports Edge Alert Bot — Architecture Draft

> Status: draft pending final provider verification and account-level coverage tests.

## 1. Design goals

- Alert-only; no wagering credentials or bet placement.
- Reproducible, leakage-safe two-year backtests.
- Provider-independent canonical data model.
- UTC storage with UTC+7 presentation/day grouping.
- Full raw-payload audit trail for every model input and price.
- Deterministic qualification and accumulator generation.
- One daily bilingual report plus material status updates.
- Operable on a small Linux VPS after local validation.

## 2. Proposed stack

- Python 3.11+
- `uv` for dependency/environment management
- Pydantic v2 for canonical provider models and configuration
- HTTPX for async provider clients
- Polars + DuckDB + Parquet for historical feature engineering/backtesting
- SQLite initially for scheduler/runtime state; PostgreSQL remains an optional production upgrade
- scikit-learn/LightGBM for tabular models
- statsmodels/scipy for Poisson and statistical confidence tests
- APScheduler for UTC+7-aware collection and alert scheduling
- python-telegram-bot for Telegram delivery
- pytest, pytest-asyncio, Hypothesis, Ruff, mypy
- Docker/systemd only after local end-to-end validation

## 3. Component boundaries

```text
Provider APIs
  ├─ football statistics adapter
  ├─ tennis statistics adapter
  ├─ bookmaker odds adapter
  └─ optional Polymarket adapter
          │
          ▼
Raw immutable snapshots ──► canonical normalizer/entity resolver
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             historical lake              runtime store
             Parquet/DuckDB                SQLite/Postgres
                    │                           │
                    ▼                           ▼
          feature/backtest pipeline      rolling 24h scanner
                    │                           │
                    ▼                           ▼
         frozen model artifacts ───────► probability engine
                                                │
                                                ▼
                                      no-vig + edge engine
                                                │
                                                ▼
                                qualification/composite ranking
                                                │
                             ┌──────────────────┴───────────────┐
                             ▼                                  ▼
                       single selections              2/3-leg optimizer
                             └──────────────────┬───────────────┘
                                                ▼
                                     bilingual report renderer
                                                │
                                                ▼
                                          Telegram sender
```

## 4. Provider interfaces

All external providers must implement typed adapters. Provider-native IDs must never leak into modeling code.

### Football statistics provider

Required capabilities:

- covered competitions/seasons/fixtures;
- teams and stable team identity mapping;
- full-time and half-time scores;
- fixture/team statistics;
- xG or a documented proxy;
- lineups/expected lineups where available;
- injuries/suspensions/news where available;
- fixture status changes.

### Tennis statistics provider

Required capabilities:

- tournaments, level, tour, surface, format, main-draw status;
- fixtures/results and retirements/walkovers;
- ATP/WTA rankings with effective dates;
- player identities;
- recent results and H2H;
- absence/return signals or enough history to derive them.

### Odds provider

Required capabilities:

- pre-match football and tennis events;
- 1xBet and/or BC.Game current decimal odds;
- required V1 markets and lines;
- exact bookmaker and market timestamps;
- historical odds or closing lines for backtesting;
- market/outcome settlement metadata or stable canonical mappings.

### Optional Polymarket provider

- Gamma API for event/market discovery;
- CLOB API for current price/orderbook/history;
- strict event and settlement-rule matching;
- corroboration only; never required for qualification.

## 5. Canonical entities

- `Sport`
- `Competition`
- `Season`
- `Tournament`
- `Event`
- `Participant` (team/player)
- `RankingSnapshot`
- `FootballTeamSnapshot`
- `TennisPlayerSnapshot`
- `AvailabilityNews`
- `MarketDefinition`
- `OutcomeDefinition`
- `OddsSnapshot`
- `MarketConsensusSnapshot`
- `FeatureSnapshot`
- `ModelArtifact`
- `Prediction`
- `QualifiedSelection`
- `AccumulatorCandidate`
- `DailyReport`
- `AlertRevision`

Every time-dependent row carries `observed_at_utc`, `effective_at_utc`, provider, provider ID, and raw snapshot reference.

## 6. Odds and no-vig logic

### Market normalization

Canonical market keys must encode period, market family, line, participant (if any), and settlement scope. Examples:

- `football:full_time:1x2`
- `football:full_time:total_goals:2.5`
- `football:first_half:total_goals:1.0`
- `football:full_time:asian_handicap:home:-0.75`
- `tennis:match:moneyline`

Do not merge bookmaker outcomes unless event identity, market family, period, line, participants, and settlement semantics match.

### No-vig conversion

For mutually exclusive outcomes with decimal odds `o_i`:

```text
raw_i = 1 / o_i
fair_i = raw_i / sum(raw_j)
```

Implement pluggable no-vig methods so proportional normalization can later be compared with power/Shin methods. Freeze one method per backtest configuration.

### Consensus

- One supported bookmaker is sufficient under the agreed V1 rule.
- If several books are present, compute a timestamp-aligned no-vig consensus and disagreement score.
- Book disagreement lowers data quality.
- Polymarket may be displayed as corroboration only when the contract is an exact semantic match.

## 7. Feature rules

### Football

At each historical decision timestamp, derive only from prior observations:

- last 10 matches overall;
- last 10 home/away-aware samples where feasible;
- opponent-adjusted attacking/defensive strength;
- xG for/against and goal conversion/prevention;
- rest days and congestion;
- H2H from the previous three seasons;
- lineup/injury/rotation/news quality flags;
- market consensus and movement available by decision time.

### Tennis

- effective-date ATP/WTA ranking;
- top-50 eligibility at event time;
- last 10 overall matches;
- last 10 on the current surface;
- opponent strength and ranking differences;
- H2H only after at least three prior meetings;
- retirement/walkover handling;
- first match after long absence hard block;
- tournament level, tour, surface, and match format.

The exact definition of `long absence` must be selected in validation and frozen (candidate values: 60/90/120 days).

## 8. Modeling and backtest design

### Decision timestamps

The production report is sent three hours before the earliest covered event of the UTC+7 day, so backtests must use odds/features captured at an equivalent historical decision time where available. Closing odds cannot substitute for report-time odds without being labeled as a proxy experiment.

### Chronological evaluation

For each league/market or tour/surface/format bucket:

1. Train on the earliest interval.
2. Tune threshold/model on a later validation interval.
3. Evaluate once on a final untouched holdout interval.
4. Require at least 50 holdout selections.
5. Freeze artifact, feature schema, no-vig method, and threshold together.

### Football candidates

- independent/Dixon-Coles Poisson baseline;
- regularized tabular classifier/regressor;
- calibrated ensemble combining model and no-vig market probability.

### Tennis candidates

- ranking-led logistic baseline;
- ranking + surface/recent-form model;
- calibrated ranking/form model with market probability as a supporting feature.

### Metrics

Primary: out-of-sample hit rate.

Mandatory guardrails:

- confidence interval/lower bound;
- calibration/Brier score;
- positive realized return at recorded report-time odds when those odds exist;
- edge over no-vig market;
- sample size;
- leakage audit.

## 9. Qualification

A deterministic policy consumes a prediction and current market snapshot. It applies the exact floors and statistical thresholds from `STRATEGY.md`. The policy emits a machine-readable reason for every pass/fail decision.

Example reject reasons:

- `ODDS_BELOW_FLOOR`
- `PROBABILITY_BELOW_FLOOR`
- `EDGE_BELOW_BACKTEST_THRESHOLD`
- `INSUFFICIENT_SAMPLE_CONFIDENCE`
- `STALE_ODDS`
- `MARKET_MAPPING_AMBIGUOUS`
- `TENNIS_PLAYER_OUTSIDE_TOP_50`
- `TENNIS_FIRST_MATCH_AFTER_ABSENCE`

## 10. Accumulator optimizer

- Input: independently qualified singles.
- Exclude two legs sharing an event ID.
- Allow cross-sport combinations.
- Require combined decimal odds > 2.00.
- Generate all eligible 2- and 3-leg combinations within a bounded slate.
- Rank by adjusted combined hit probability.
- Start with the product of leg probabilities only across separate events, then apply a configurable same-day/team/player/dependence penalty where evidence warrants it.
- Return exactly the best valid two-leg and best valid three-leg combinations when each exists.

## 11. Alert state machine

```text
UNSEEN -> QUALIFIED -> ALERTED -> STILL_VALID
                         |             |
                         └─────────────┴──> EDGE_EXPIRED
UNSEEN/REJECTED -> QUALIFIED_AFTER_REPORT -> NEW update
```

A price change alone updates storage but does not trigger Telegram. A message is triggered only by a status transition or material news assessment.

## 12. Security and operations

- Secrets only in environment variables or a root-readable service environment file; never commit them.
- Read-only provider credentials.
- Telegram bot token has no relation to bookmaker accounts.
- Structured logs must redact tokens and query-string API keys.
- Persist raw provider responses before transformation.
- Cache entity mappings and API responses to control costs.
- Monitor stale feeds, missing competitions, mapping collisions, scheduler lag, and Telegram failures.
- Never silently continue with stale odds.

## 13. Open provider gates

Before implementation is considered production-capable, verify with trial/API keys:

1. Exact 1xBet and BC.Game market availability for all covered football competitions and tennis event levels.
2. Historical report-time odds availability, not only closing lines.
3. Full V1 football market/line coverage.
4. Football xG, lineup, injury, and historical-season coverage.
5. Tennis ranking effective dates, surface, retirements, main-draw qualification, and H2H completeness.
6. Redistribution/display rights for Telegram alerts under each provider’s terms.
7. Request limits and monthly cost at a final-24h polling cadence.
