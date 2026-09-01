# Sports Edge Alert Bot — V1 Strategy Specification

## 1. Purpose and safety boundary

Build an alert-only Telegram bot that identifies statistically reliable positive-edge pre-match selections for covered football and tennis events.

The system must never:

- place bets;
- connect to bookmaker wagering credentials;
- recommend stake sizes;
- represent a selection as guaranteed to win.

## 2. Time and alert scope

- Display and group events using UTC+7.
- Analyze pre-match markets only.
- Continuously refresh covered events during the final 24 hours before start.
- Send one combined global daily alert three hours before the earliest covered event of that UTC+7 calendar day.
- That report may include qualifying events that start later the same day.
- If no selection qualifies, send a bilingual "No qualifying bets today" message.
- Do not send another Telegram message for price movement alone.
- Continue monitoring internally after the daily report.
- Send an update only when:
  - a new selection qualifies;
  - a previously alerted selection loses qualification or its edge expires; or
  - major lineup, injury, suspension, withdrawal, or scheduling news materially changes the assessment.
- Preserve the original alert. Updates label selections as `NEW`, `STILL VALID`, or `EDGE EXPIRED`.

## 3. Universal selection rules

A single selection qualifies only when all conditions hold:

1. The model probability exceeds the no-vig market probability.
2. The positive edge is statistically reliable under the applicable backtest bucket.
3. The minimum edge threshold is selected out-of-sample by backtesting, separately for each sport/market segment.
4. The current executable decimal odds meet the sport-specific floor.
5. The estimated probability meets the sport-specific absolute floor.
6. Historical validation has at least 50 qualifying out-of-sample observations and passes the configured statistical-confidence rule.

There is no maximum odds limit if all qualification rules pass.

### Football floors

- Decimal odds: at least 1.50.
- Estimated probability: at least 60%.

### Tennis floors

- Decimal odds: at least 1.30.
- Estimated probability: at least 65%.

## 4. Market-price logic

- Use bookmaker prices as the primary executable-price source.
- A matching price from either 1xBet or BC.Game is sufficient, subject to provider availability and lawful access.
- Use additional bookmakers when available; agreement improves the data-quality score.
- Remove bookmaker margin before deriving market-implied probabilities.
- Use Polymarket as optional probability corroboration when an equivalent, unambiguously settled contract exists.
- When Polymarket has no equivalent market, use the available bookmaker market or bookmaker consensus.
- Never treat unmatched markets or materially different settlement rules as equivalent.

## 5. Football coverage

### Competitions

- Premier League
- La Liga
- Serie A
- Eredivisie
- UEFA Champions League main competition
- UEFA Europa League main competition

Exclude domestic cups and UEFA qualifying rounds.

### V1 markets

Full-match:

- 1X2 result
- double chance
- draw no bet
- Asian handicap
- total goals
- both teams to score
- team total goals

First half:

- first-half result
- first-half total goals

Defer player props, goalscorers, shots, corners, cards, and second-half-only markets until the result/goal system is validated.

### Football candidate presentation

- Evaluate every supported market for every covered match.
- Include every independently qualifying selection in the daily report.
- Rank selections rather than forcing one pick per match.
- Correlated selections from one match may appear as singles, but cannot appear together in an accumulator.

### Football model candidates

Backtest and compare:

1. xG/Poisson models;
2. machine-learning models; and
3. market-adjusted ensembles.

Choose the best calibrated, out-of-sample model by league and market.

Candidate features include:

- rolling last 10 team matches;
- home/away splits and home advantage;
- attacking and defensive xG or closest licensed equivalent;
- opponent-adjusted form;
- all H2H meetings from the previous three seasons;
- injuries, suspensions, expected/confirmed lineups, rotation, and fixture congestion;
- manager changes, neutral venue, weather, and schedule uncertainty;
- current and historical no-vig market probabilities and line movement.

No contextual football condition is an unconditional block in V1. Uncertainty lowers data quality and may prevent a pick from meeting the composite/confidence thresholds.

## 6. Tennis coverage

### Events and players

Include men’s and women’s singles in:

- ATP/WTA 500;
- ATP/WTA 1000;
- ATP/WTA Tour Finals; and
- Grand Slams.

Exclude 250-level events, Challenger, ITF, qualifying matches, and doubles.

Only recommend a player currently ranked ATP/WTA No. 1–50. Never recommend backing No. 51 or lower.

### V1 market

- Match winner only.

### Tennis model

Use a ranking-led model adjusted by:

- last 10 matches overall;
- last 10 matches on the current surface;
- opponent strength;
- surface-specific performance;
- recent serve/return performance when licensed data is available;
- fitness, injury, fatigue, travel, scheduling, and withdrawals;
- match format; and
- H2H only when the players have met at least three times.

Hard blocks:

- first match after a long absence;
- unreliable or conflicting odds.

## 7. Backtesting and threshold selection

- Use the last two completed seasons/years.
- Use chronological train/validation/test or rolling-origin splits; never random splits that leak future information.
- Use only information and prices that would have been available at the simulated decision time.
- Primary model-selection metric: out-of-sample hit rate.
- Also enforce positive edge against the no-vig market and reject negative-expectation configurations.
- Evaluate calibration and uncertainty so a high hit rate from a small or biased sample cannot qualify.
- Absolute minimum: 50 out-of-sample qualifying bets per validation bucket.

Segmentation:

- Football: league × market.
- Tennis: tour × surface × match format.

Thresholds and model choices must be frozen before evaluating the final holdout period.

## 8. Composite ranking

Rank qualifying singles using a documented composite of:

- estimated probability;
- no-vig edge;
- historical hit rate and uncertainty;
- data-quality score; and
- odds stability.

The score must be monotonic in probability and edge, penalize low-quality inputs, and be calibrated/frozen from historical validation rather than tuned to a current slate.

## 9. Accumulators

Generate and display separately:

- the best two-leg accumulator; and
- the best three-leg accumulator.

Rules:

- combined decimal odds must exceed 2.00;
- every leg must independently qualify as a single;
- no two legs may come from the same match;
- football and tennis legs may be mixed;
- rank eligible combinations by highest combined predicted hit probability;
- compute combined probability as a simple product only when cross-event dependence is negligible; otherwise apply a dependence penalty or exclude the combination.

## 10. Telegram content

Messages must be bilingual English and Bahasa Indonesia.

For every selection show:

- competition/tournament;
- UTC+7 start time;
- event;
- market and selection;
- current decimal odds and source;
- model probability;
- no-vig market probability;
- edge;
- historical hit rate and sample size;
- composite rank/score;
- data-quality grade;
- odds movement;
- concise bilingual reasoning;
- relevant lineup, injury, schedule, or data warning;
- status (`NEW`, `STILL VALID`, `EDGE EXPIRED`).

## 11. V1 exclusions

- Automated bet placement
- Bookmaker account or wagering credentials
- Stake sizing
- Live/in-play analysis
- Performance dashboard or scheduled result reports
- Player props
- Corners and cards
- Tennis set/game markets

## 12. Launch rule

The alert bot may launch immediately after the two-year historical backtests and all data-quality/test gates pass. The first production messages should still be clearly labeled as model-generated estimates, not guarantees.
