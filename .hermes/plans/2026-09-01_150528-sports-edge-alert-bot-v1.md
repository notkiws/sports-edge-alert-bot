# Sports Edge Alert Bot V1 Implementation Plan

> **For Hermes:** Execute this plan task-by-task with strict test-driven development and review each provider gate before continuing.

**Goal:** Build a tested, alert-only Telegram system that backtests and identifies statistically reliable positive-edge football and tennis pre-match selections under `STRATEGY.md`.

**Architecture:** Typed provider adapters persist immutable raw snapshots and normalize them into provider-independent entities. A leakage-safe historical pipeline trains/finalizes segmented models, while a runtime scanner evaluates current markets, qualifies/ranks singles, generates the best two- and three-leg accumulators, and sends one bilingual UTC+7 daily report plus material status updates.

**Tech Stack:** Python 3.11+, uv, Pydantic v2, HTTPX, Polars, DuckDB/Parquet, SQLite, scikit-learn/LightGBM, scipy/statsmodels, APScheduler, python-telegram-bot, pytest/Hypothesis, Ruff, mypy.

---

## Phase 0 — Provider proof before implementation

### Task 1: Obtain provider trial access and freeze the source decision

**Objective:** Prove that selected providers supply every mandatory field/market and that two-year historical data is economically available.

**Files:**
- Modify: `DATA_SOURCES.md`
- Create: `docs/provider-matrix.md`
- Create: `samples/redacted/README.md`

**Steps:**

1. Request or purchase trial access only after reviewing current terms/prices for Odds-API.io, the chosen football statistics provider, and the chosen tennis provider.
2. Fetch and save redacted sample responses for every proof listed in `DATA_SOURCES.md`.
3. Record endpoint, timestamp, competition/tournament, available markets, historical depth, rate limits, and license/display constraints in `docs/provider-matrix.md`.
4. Verify that historical odds correspond to report-time snapshots or explicitly record that only closing lines exist.
5. Calculate expected request volume for final-24h polling and the one-report/update policy.
6. Stop and redesign if mandatory report-time history or required markets are unavailable/too expensive.
7. Commit: `docs: verify sports data provider coverage`.

**Gate:** Do not implement provider-specific production adapters until this task passes.

## Phase 1 — Reproducible project foundation

### Task 2: Bootstrap the Python package and quality gates

**Objective:** Create a minimal installable package with deterministic tooling.

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/sports_edge/__init__.py`
- Create: `tests/test_package.py`

**TDD steps:**

1. Write `tests/test_package.py` to import `sports_edge` and assert a version is exposed.
2. Run `uv run pytest tests/test_package.py -v`; verify RED because the package does not exist.
3. Add the minimal package metadata and `__version__`.
4. Run the test; verify GREEN.
5. Configure pytest, Ruff, and mypy in `pyproject.toml`.
6. Run `uv run pytest -q`, `uv run ruff check .`, and `uv run mypy src`.
7. Commit: `chore: bootstrap sports edge package`.

### Task 3: Define configuration and secret handling

**Objective:** Load validated non-secret settings and secret provider tokens without leaking them.

**Files:**
- Create: `src/sports_edge/config.py`
- Create: `tests/unit/test_config.py`
- Modify: `.env.example`

**TDD steps:**

1. Test required UTC+7 timezone, sport odds/probability floors, covered competitions, polling cadence, and missing-secret errors.
2. Verify RED.
3. Implement Pydantic settings with tokens excluded from repr/log output.
4. Verify GREEN and run the full suite.
5. Commit: `feat: add validated runtime configuration`.

## Phase 2 — Canonical domain and persistence

### Task 4: Implement canonical event and market models

**Objective:** Represent football/tennis events, markets, outcomes, and timestamped odds without provider-specific assumptions.

**Files:**
- Create: `src/sports_edge/domain/events.py`
- Create: `src/sports_edge/domain/markets.py`
- Create: `src/sports_edge/domain/odds.py`
- Create: `tests/unit/domain/test_events.py`
- Create: `tests/unit/domain/test_markets.py`

**TDD slices:**

1. UTC-only event timestamps and UTC+7 day grouping.
2. Canonical football period/family/line keys.
3. Tennis match-winner keys.
4. Decimal-odds validation and source timestamp requirements.
5. Market-semantic mismatch rejection.
6. Commit: `feat: add canonical sports market domain`.

### Task 5: Implement raw snapshots and runtime storage

**Objective:** Preserve provider payloads immutably and store normalized runtime state idempotently.

**Files:**
- Create: `src/sports_edge/storage/raw.py`
- Create: `src/sports_edge/storage/runtime.py`
- Create: `src/sports_edge/storage/schema.sql`
- Create: `tests/integration/test_storage.py`

**TDD slices:**

1. Content-addressed raw payload persistence.
2. Idempotent odds snapshot insertion.
3. Provider ID to canonical ID mappings.
4. Daily report and alert-revision state.
5. Verify with a temporary SQLite database and filesystem.
6. Commit: `feat: persist raw and normalized snapshots`.

## Phase 3 — Provider adapters

### Task 6: Implement the odds provider adapter

**Objective:** Fetch and normalize 1xBet/BC.Game football and tennis pre-match odds from the verified aggregator.

**Files:**
- Create: `src/sports_edge/providers/base.py`
- Create: `src/sports_edge/providers/odds_api_io.py`
- Create: `tests/fixtures/odds_api_io/*.json`
- Create: `tests/unit/providers/test_odds_api_io.py`
- Create: `tests/contract/test_odds_provider.py`

**TDD slices:**

1. Parse bookmaker, event, market, period, line, outcome, odds, and update timestamp.
2. Normalize every V1 football market from redacted fixtures.
3. Normalize tennis match-winner markets.
4. Reject ambiguous/unmapped markets instead of guessing.
5. Handle rate limits, transient errors, stale data, and partial bookmaker coverage.
6. Run contract tests against the trial API only when an explicit environment flag is set.
7. Commit: `feat: integrate pre-match odds provider`.

### Task 7: Implement the football statistics adapter

**Objective:** Normalize covered fixtures, scores, xG/statistics, lineups, and news/availability.

**Files:**
- Create: `src/sports_edge/providers/football.py`
- Create: `tests/fixtures/football_provider/*.json`
- Create: `tests/unit/providers/test_football_provider.py`
- Create: `tests/contract/test_football_provider.py`

**TDD slices:**

1. Competition allowlist and qualifier/cup exclusion.
2. Stable team/event mapping.
3. Full-time and first-half results.
4. xG/statistics availability and missingness flags.
5. Expected/confirmed lineups and availability/news quality.
6. Fixture postponement/rescheduling.
7. Commit: `feat: integrate football statistics provider`.

### Task 8: Implement the tennis statistics adapter

**Objective:** Normalize eligible tournaments, rankings, surfaces, results, absence signals, and H2H.

**Files:**
- Create: `src/sports_edge/providers/tennis.py`
- Create: `tests/fixtures/tennis_provider/*.json`
- Create: `tests/unit/providers/test_tennis_provider.py`
- Create: `tests/contract/test_tennis_provider.py`

**TDD slices:**

1. Include ATP/WTA 500+, Finals, and Slams main draws.
2. Exclude 250/Challenger/ITF/qualifying/doubles.
3. Apply ranking effective at event time.
4. Encode surface and match format.
5. Identify retirement/walkover and first match after configured absence.
6. Count only prior H2H and activate it at three meetings.
7. Commit: `feat: integrate tennis statistics provider`.

### Task 9: Implement optional Polymarket corroboration

**Objective:** Match exact public Polymarket contracts without making them required.

**Files:**
- Create: `src/sports_edge/providers/polymarket.py`
- Create: `tests/unit/providers/test_polymarket.py`

**TDD slices:**

1. Parse Gamma event/market discovery and CLOB prices.
2. Require exact participants, event, outcome, timing, and settlement semantics.
3. Return no corroboration when mapping is ambiguous.
4. Verify no wallet/trading authentication exists in the package.
5. Commit: `feat: add optional Polymarket corroboration`.

## Phase 4 — Historical features and backtests

### Task 10: Build leakage-safe football features

**Objective:** Produce point-in-time football features under the last-10/H2H rules.

**Files:**
- Create: `src/sports_edge/features/football.py`
- Create: `tests/unit/features/test_football_features.py`
- Create: `tests/leakage/test_football_time_integrity.py`

**TDD slices:**

1. Last 10 excludes current/future match.
2. Home/away and opponent-strength features.
3. H2H uses only prior meetings from the previous three seasons.
4. Missing xG/lineup/news lowers quality rather than leaking substitutes.
5. Every feature row records an `as_of_utc` cutoff.
6. Commit: `feat: build point-in-time football features`.

### Task 11: Build leakage-safe tennis features

**Objective:** Produce point-in-time ranking, form, surface, absence, and H2H features.

**Files:**
- Create: `src/sports_edge/features/tennis.py`
- Create: `tests/unit/features/test_tennis_features.py`
- Create: `tests/leakage/test_tennis_time_integrity.py`

**TDD slices:**

1. Effective-date top-50 ranking filter.
2. Last 10 overall and last 10 surface matches exclude current/future data.
3. H2H activates only after three prior meetings.
4. Long-absence block uses only prior dates.
5. Retirement/walkover outcomes are handled consistently.
6. Commit: `feat: build point-in-time tennis features`.

### Task 12: Implement no-vig and market consensus

**Objective:** Convert complete market prices to fair probabilities and quantify disagreement/staleness.

**Files:**
- Create: `src/sports_edge/markets/no_vig.py`
- Create: `src/sports_edge/markets/consensus.py`
- Create: `tests/unit/markets/test_no_vig.py`
- Create: `tests/property/test_market_math.py`

**TDD slices:**

1. Proportional no-vig probabilities sum to one.
2. Reject incomplete mutually exclusive markets.
3. Align bookmaker snapshots by freshness window.
4. Compute consensus/disagreement with one or more books.
5. Property-test valid odds ranges and invariants.
6. Commit: `feat: calculate fair market probabilities`.

### Task 13: Implement chronological model comparison

**Objective:** Compare the agreed football and tennis model families without leakage.

**Files:**
- Create: `src/sports_edge/modeling/splits.py`
- Create: `src/sports_edge/modeling/football.py`
- Create: `src/sports_edge/modeling/tennis.py`
- Create: `src/sports_edge/modeling/calibration.py`
- Create: `tests/unit/modeling/*.py`
- Create: `tests/leakage/test_model_splits.py`

**TDD slices:**

1. Chronological train/validation/holdout boundaries.
2. Football Poisson baseline.
3. Football tabular baseline.
4. Football market-adjusted calibrated ensemble.
5. Tennis ranking-led logistic baseline and adjusted model.
6. Serialize model, schema, segment, thresholds, and data cutoff as one immutable artifact.
7. Commit: `feat: add chronological sports model pipeline`.

### Task 14: Implement backtest qualification and threshold freezing

**Objective:** Select statistically reliable edge thresholds by segment and evaluate once on holdout.

**Files:**
- Create: `src/sports_edge/backtest/runner.py`
- Create: `src/sports_edge/backtest/thresholds.py`
- Create: `src/sports_edge/backtest/report.py`
- Create: `tests/unit/backtest/test_thresholds.py`
- Create: `tests/integration/test_backtest_runner.py`

**TDD slices:**

1. Enforce sport-specific odds and probability floors.
2. Enforce minimum 50 holdout picks.
3. Select thresholds only from train/validation.
4. Report hit rate, confidence interval, Brier score, edge, sample, and realized return.
5. Reject configurations with no reliable positive edge.
6. Produce machine-readable and Markdown reports.
7. Commit: `feat: validate and freeze edge strategies`.

## Phase 5 — Runtime selection and alerts

### Task 15: Implement deterministic qualification and ranking

**Objective:** Apply frozen artifacts to current markets with explainable pass/fail reasons.

**Files:**
- Create: `src/sports_edge/selection/qualifier.py`
- Create: `src/sports_edge/selection/ranking.py`
- Create: `tests/unit/selection/test_qualifier.py`
- Create: `tests/unit/selection/test_ranking.py`

**TDD slices:**

1. Every universal qualification condition and rejection code.
2. Football and tennis floors.
3. Top-50/absence tennis rules.
4. Stale/ambiguous odds rejection.
5. Composite score monotonicity and quality penalty.
6. Stable deterministic ranking.
7. Commit: `feat: qualify and rank positive edge selections`.

### Task 16: Implement accumulator generation

**Objective:** Return the best valid two- and three-leg combinations.

**Files:**
- Create: `src/sports_edge/selection/accumulators.py`
- Create: `tests/unit/selection/test_accumulators.py`
- Create: `tests/property/test_accumulator_rules.py`

**TDD slices:**

1. Only qualified singles are accepted.
2. Exclude same-event legs.
3. Allow cross-sport legs.
4. Require combined odds > 2.00.
5. Rank by adjusted combined hit probability.
6. Return best two-leg and best three-leg independently or no result when none exists.
7. Commit: `feat: generate constrained accumulators`.

### Task 17: Implement bilingual Telegram rendering

**Objective:** Render complete, readable English/Bahasa reports and updates.

**Files:**
- Create: `src/sports_edge/alerts/render.py`
- Create: `src/sports_edge/alerts/templates.py`
- Create: `tests/golden/alerts/*.md`
- Create: `tests/unit/alerts/test_render.py`

**TDD slices:**

1. Golden-file report with every required field.
2. No-picks bilingual report.
3. Best 2-leg/3-leg sections.
4. `NEW`, `STILL VALID`, and `EDGE EXPIRED` updates.
5. Telegram message-length chunking without splitting a selection.
6. Commit: `feat: render bilingual Telegram reports`.

### Task 18: Implement scheduler and alert state machine

**Objective:** Scan final-24h events and send exactly one UTC+7 report plus material updates.

**Files:**
- Create: `src/sports_edge/runtime/scanner.py`
- Create: `src/sports_edge/runtime/scheduler.py`
- Create: `src/sports_edge/runtime/state.py`
- Create: `tests/unit/runtime/test_schedule.py`
- Create: `tests/integration/test_alert_state_machine.py`

**TDD slices:**

1. Determine UTC+7 day and earliest event.
2. Schedule report exactly three hours before earliest event.
3. Prevent duplicate daily reports across restarts.
4. Do not alert for odds movement alone.
5. Alert on new qualification, expiry, or material news state transition.
6. Recover safely from provider/Telegram failures without duplicate sends.
7. Commit: `feat: schedule daily reports and status updates`.

### Task 19: Implement Telegram transport

**Objective:** Send rendered messages through a restricted alert-only bot.

**Files:**
- Create: `src/sports_edge/alerts/telegram.py`
- Create: `tests/unit/alerts/test_telegram.py`
- Create: `scripts/send_test_alert.py`

**TDD slices:**

1. Send to configured chat ID.
2. Retry transient failures idempotently.
3. Redact token from logs/errors.
4. Refuse any unsupported command or wagering action.
5. Send a real test message only after the user provides the token/chat ID locally.
6. Commit: `feat: deliver alert-only Telegram messages`.

## Phase 6 — End-to-end validation and deployment

### Task 20: Run historical backtests and freeze V1 artifacts

**Objective:** Produce real two-season holdout evidence for every enabled segment.

**Files:**
- Create: `configs/backtest_v1.yaml`
- Create: `artifacts/.gitkeep`
- Generate: `reports/backtest_v1.md`
- Generate: `reports/backtest_v1.json`

**Steps:**

1. Ingest and validate the two completed seasons/years.
2. Run leakage checks before training.
3. Train/tune on chronological pre-holdout data.
4. Evaluate once on holdout.
5. Disable every segment that fails sample/confidence/edge gates.
6. Freeze passing artifacts with data hashes and config hashes.
7. Review actual results with the user; never fabricate or extrapolate missing segments.
8. Commit only configuration/reports that contain no licensed raw data.
9. Commit: `model: freeze validated v1 strategies`.

### Task 21: Exercise a full dry run

**Objective:** Prove provider collection → prediction → qualification → accumulator → rendering → Telegram transport.

**Files:**
- Create: `tests/e2e/test_daily_pipeline.py`
- Create: `scripts/dry_run_daily.py`

**Steps:**

1. Test deterministic end-to-end behavior with recorded redacted fixtures.
2. Run a live read-only dry run with Telegram sending disabled.
3. Inspect every candidate and rejection reason.
4. Send one explicit test report to Telegram.
5. Verify no bookmaker credential or bet-placement code exists using repository search.
6. Run all gates: `uv run pytest -q`, `uv run ruff check .`, `uv run mypy src`.
7. Commit: `test: verify daily alert pipeline end to end`.

### Task 22: Package and deploy after explicit approval

**Objective:** Run the validated alert bot reliably without changing any unrelated trading-bot service.

**Files:**
- Create: `Dockerfile`
- Create: `deploy/sports-edge.service`
- Create: `deploy/README.md`
- Create: `scripts/healthcheck.py`

**Steps:**

1. Build and run the container/service locally.
2. Verify health, scheduler time, read-only provider access, state persistence, and log redaction.
3. Obtain explicit approval for the target VPS and deployment scope.
4. Install under a separate non-root service/user directory.
5. Never reuse BTC bot or bookmaker credentials.
6. Verify one dry-run cycle on the target before enabling Telegram delivery.
7. Commit: `ops: package sports edge alert service`.

## Final acceptance criteria

- [ ] Every enabled segment passed a real chronological two-season/year backtest.
- [ ] No look-ahead leakage; report-time prices are used or limitations are explicit.
- [ ] Every single satisfies odds, probability, edge, and statistical-confidence rules.
- [ ] Best two-leg and three-leg accumulators satisfy all constraints.
- [ ] One combined UTC+7 report is scheduled correctly.
- [ ] Price movement alone never sends an update.
- [ ] Bilingual messages include every required field.
- [ ] No wagering credentials, staking, or automatic betting code exists.
- [ ] Provider licensing, cost, and exact coverage are documented.
- [ ] Full test, lint, type, dry-run, and real Telegram test gates pass.
