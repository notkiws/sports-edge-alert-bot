# Sports Probability Alert Bot — V1 Strategy Specification

## 1. Purpose and safety boundary

Build a private, personal-use Telegram bot that produces pre-match probability forecasts for covered football matches and positive-edge tennis alerts when an independent model disagrees favorably with an executable Polymarket price.

The system must never:

- place bets;
- connect to bookmaker accounts or wagering credentials;
- recommend stakes;
- describe any prediction as guaranteed;
- sell, redistribute, or expose source datasets as a data feed.

Football selections are probability forecasts, **not value-bet claims**, because football bookmaker odds are not used in V1.

## 2. Time and alert scope

- Store timestamps in UTC and display/group events using UTC+7 (`Asia/Jakarta`).
- Analyze pre-match events only.
- Send one combined global daily alert three hours before the earliest covered event of that UTC+7 calendar day.
- Include qualifying later events from the same day.
- If nothing qualifies, send a bilingual “No qualifying selections today” message.
- Preserve original alerts and send an update only for a material status change, cancellation/withdrawal, or material source-data correction.

## 3. Football coverage and source

### Source

Use football-data.org as the V1 football source.

The free account must be tested for exact competition and historical-season availability before a competition is enabled. If Europa League is unavailable under the free account, disable it rather than scraping another website.

### Competitions

Target:

- Premier League
- La Liga
- Serie A
- Eredivisie
- UEFA Champions League main competition
- UEFA Europa League main competition, only if available under the selected account

Exclude domestic cups and UEFA qualifying rounds.

### Football data available to the model

Use only point-in-time fields lawfully available from football-data.org, including:

- fixtures and schedules;
- full-time and half-time results;
- league table/position;
- home and away teams;
- match status;
- available lineups, scorers, cards, or deeper fields only when the account returns them.

Do not assume free access to xG, injuries, suspensions, or expected lineups. Missing fields lower data quality; they must never be fabricated.

## 4. Football prediction markets

Evaluate probability forecasts derivable from the modeled full-time/half-time score distributions:

Full match:

- 1X2 result
- double chance
- draw no bet
- Asian handicap outcome probabilities
- total goals
- both teams to score
- team total goals

First half, only when historical half-time coverage and calibration are sufficient:

- first-half result
- first-half total goals

Defer player props, goalscorers, shots, corners, cards, and second-half-only markets.

## 5. Football qualification and presentation

For each match:

1. Estimate probabilities for every supported canonical option.
2. Exclude logically redundant duplicate selections where one option adds no useful information.
3. Rank remaining options by calibrated estimated probability, historical confidence, and data quality.
4. Display only options whose individual estimated probability is at least **60%**.
5. Display at most **three** options per match.
6. If no option reaches 60%, skip the entire match.

No football odds, implied probabilities, edge, expected value, or “value bet” labels appear in V1.

### Football model candidates

Backtest:

1. independent/Dixon-Coles-style Poisson score models;
2. regularized machine-learning models using result/form features; and
3. calibrated ensembles of the strongest point-in-time models.

Use a rolling last-10-match form window and all prior H2H meetings from the previous three seasons. Features may include:

- goals for/against;
- home/away splits;
- opponent-adjusted strength;
- league position and points form;
- rest days and fixture congestion when derivable;
- prior full-time and half-time score distributions;
- point-in-time lineup/deep-data fields only when genuinely returned.

Choose and calibrate models separately by league and market when sample size permits; otherwise use a documented pooled model with league as a feature.

## 6. Tennis coverage and sources

### Sources

- **Historical modeling:** free Tennis-Data.co.uk files, for private/personal use only and subject to the source’s copyright terms.
- **Current market discovery and executable price:** public Polymarket Gamma and CLOB APIs.

Do not scrape ATP/WTA websites or use unavailable/stale Jeff Sackmann mirrors.

### Events and players

Target men’s and women’s singles in:

- ATP/WTA 500;
- ATP/WTA 1000;
- Tour Finals; and
- Grand Slams.

Exclude 250-level events, Challenger, ITF, qualifying matches, and doubles.

Only recommend backing a player whose latest reliable ranking-at-tournament is No. 1–50. If ranking freshness is insufficient, reject the selection.

### Tennis market

- Individual match winner only.
- Do not substitute tournament-winner/outright contracts for match-winner contracts.
- Only analyze an event when the Polymarket contract unambiguously matches the players, tournament, round/match, start window, outcome, and settlement rules.

## 7. Tennis model and edge logic

Use an independent surface-aware model derived from historical Tennis-Data records.

Candidate features:

- ranking and ranking difference at tournament time;
- surface-aware Elo or equivalent strength rating;
- last 10 matches overall;
- last 10 matches on the current surface;
- opponent strength;
- recent retirement/walkover history;
- fatigue/rest when derivable;
- match format;
- H2H only after at least three prior meetings.

Hard blocks:

- first match after a validated long-absence threshold;
- stale or unreliable ranking input;
- ambiguous event/contract mapping;
- missing or stale CLOB order book;
- unreliable/conflicting historical inputs.

### Executable Polymarket price

- Use the CLOB best ask or size-specific ask VWAP for buying the recommended outcome.
- Never use Gamma midpoint, displayed probability, or last trade as the executable price.
- Include spread and available depth in data quality.
- Add configured fee, slippage, and staleness buffers.

### Tennis qualification

A tennis selection qualifies only when:

1. independent model probability is at least **65%**;
2. latest reliable ranking is No. 1–50;
3. the model probability exceeds the executable Polymarket ask probability after fees/slippage/staleness buffer;
4. the edge exceeds a statistically validated minimum selected out-of-sample;
5. the relevant model bucket has at least 50 qualifying historical holdout observations or a statistically justified pooled fallback;
6. the Polymarket market is active, unambiguous, and has executable ask depth.

Preserve the earlier minimum decimal-odds rule of 1.30 by requiring effective buy price (including fees/slippage) to be no greater than approximately **0.7692**. A lower market price is allowed only if model probability remains at least 65% and the edge is statistically reliable.

## 8. Backtesting

Use the last two completed seasons/years where the selected free datasets provide reliable coverage.

### General rules

- Use chronological train/validation/holdout or rolling-origin splits.
- Never random-split time-series sports data.
- Use only information available before the simulated match.
- Freeze features, model, calibration, and thresholds before final holdout evaluation.
- Require an absolute minimum of 50 holdout selections per validated bucket, or use a documented pooled fallback.
- Report hit rate, confidence interval, calibration/Brier score, sample size, and data-quality limitations.

### Football validation

- Primary selection metric: out-of-sample hit rate and probability calibration.
- Validate whether options labeled 60%, 70%, etc. achieve corresponding frequencies.
- There is no ROI/edge claim because no historical football odds are used.

### Tennis validation

- Primary metrics: out-of-sample hit rate, calibration, and edge versus historical available closing/recorded prices.
- Tennis-Data closing odds are not equivalent to the future production decision-time CLOB ask; label this limitation explicitly.
- Start storing Polymarket decision-time snapshots from day one to build a true forward-validation set.

## 9. Ranking

### Football

Rank eligible options using a documented composite of:

- calibrated probability;
- historical hit-rate confidence;
- sample size;
- model agreement; and
- data quality.

Probability is the dominant component. Show at most three individually qualifying options per match.

### Tennis

Rank eligible selections using:

- independent model probability;
- executable-price edge after buffers;
- calibration/sample confidence;
- CLOB spread/depth/freshness; and
- data quality.

## 10. Telegram content

Messages must be bilingual English and Bahasa Indonesia.

### Football selection fields

- competition;
- UTC+7 start time;
- match;
- market and selection;
- estimated probability;
- historical hit rate and sample size;
- rank/data-quality grade;
- concise bilingual reasoning;
- relevant data warning;
- explicit label: `PROBABILITY FORECAST — ODDS NOT EVALUATED`.

### Tennis selection fields

- tournament and surface;
- UTC+7 start time;
- match and recommended player;
- model probability;
- executable Polymarket ask/VWAP and equivalent decimal odds;
- edge after buffers;
- historical hit rate and sample size;
- CLOB spread/depth/freshness;
- rank/data-quality grade;
- concise bilingual reasoning and warnings;
- Polymarket market link/ID when available.

## 11. V1 exclusions

- Automated bet placement
- Bookmaker credentials
- Stake sizing
- Live/in-play analysis
- Football bookmaker odds or value claims
- Accumulators/parlays
- Player props
- Corners/cards
- Tennis set/game markets
- Commercial/subscription distribution
- Automated ATP/WTA website scraping

## 12. Launch rule

The bot may send football probability forecasts after the two-season chronological football backtest and calibration gates pass.

Tennis alerts may launch after the independent model’s historical validation passes, but they must remain labeled experimental until enough forward Polymarket decision-time snapshots have accumulated to validate real executable edge.
