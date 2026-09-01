# Data Source Evaluation

> Verified against accessible official documentation and public endpoints in September 2026. Provider account/trial tests remain mandatory before production use.

## 1. Decision summary

### Free prototype

- **Football fixtures/results/tables:** football-data.org Free.
- **Limited current football/tennis odds:** The Odds API Free (500 credits/month).
- **Optional public market data:** Polymarket Gamma/CLOB APIs.
- **Football research data:** StatsBomb Open Data where competition/season coverage happens to match.
- **Tennis historical bootstrap:** Tennis-Data.co.uk free spreadsheet downloads, subject to copyright/licensing confirmation.
- **Tennis operational trial:** API-Tennis 14-day trial.

This is enough to implement and exercise provider abstractions, normalization, no-vig calculations, model baselines, alert rendering, scheduling, and forward snapshot collection. It is **not enough to certify the frozen V1 strategy**, because free plans do not provide complete two-year report-time odds, all target markets, current xG/injury coverage, and a permanent operational tennis feed.

### Budget-conscious validated V1

- **Football statistics:** Sportmonks, or football-data.org for a reduced non-xG baseline.
- **Tennis statistics:** API-Tennis Starter, after its 14-day trial passes all coverage/licensing gates.
- **Current and historical bookmaker odds:** The Odds API paid plan.
- **Optional corroboration/executable exchange depth:** Polymarket public APIs.

### Stronger production option

- **Football:** Sportmonks with required league and xG bundles.
- **Tennis:** Sportradar Tennis Base under a commercial contract.
- **Odds:** OpticOdds or another contracted normalized odds feed when limits, streaming, freshness, and wider bookmaker coverage justify the cost.

## 2. Free sources

### football-data.org Free

Official URLs:

- Coverage: https://www.football-data.org/coverage
- Pricing: https://www.football-data.org/pricing
- Documentation: https://www.football-data.org/documentation/quickstart

Verified free-tier terms/features:

- €0 forever;
- 12 competitions;
- delayed scores/schedules;
- fixtures and league tables;
- 10 calls/minute.

The free highlights include Premier League, La Liga, Serie A, Eredivisie, and Champions League. Europa League is present in the provider’s overall catalogue, but its availability under the exact free account must be tested.

Useful for fixtures, results, tables, and result-based baseline models. Not sufficient alone for current injuries, comprehensive xG, historical bookmaker odds, or all V1 markets.

### The Odds API Free

Official URLs:

- Home/pricing: https://the-odds-api.com/
- Documentation: https://the-odds-api.com/liveapi/guides/v4/
- Sports: https://the-odds-api.com/sports-odds-data/sports-apis.html
- Bookmakers: https://the-odds-api.com/sports-odds-data/bookmaker-apis.html
- Historical data: https://the-odds-api.com/historical-odds-data/

Verified:

- Free tier: 500 credits/month.
- Football and tennis current/upcoming odds.
- All six target football competitions are listed.
- 1xBet appears in EU bookmaker coverage.
- Featured markets include 1X2/moneyline, spreads/handicaps, and totals.
- Historical odds are **paid-only**.

Use the free plan for low-frequency development snapshots, not continuous final-24h monitoring. It cannot reproduce a two-year three-hours-before-report backtest.

### Polymarket public APIs

Official endpoints:

- Gamma discovery: https://gamma-api.polymarket.com
- CLOB prices/books/history: https://clob.polymarket.com
- Data API: https://data-api.polymarket.com

Public market discovery and market-data reads require no authentication. Trading authentication is out of scope.

Verified sports metadata includes broad football and tennis coverage. Coverage is opportunistic rather than complete, and many exact football derivative markets will be absent. Use Polymarket only for exact semantic matches.

For executable exchange prices, use the CLOB order book and calculate size-specific VWAP. Do not treat a midpoint or last trade as an executable quote.

Direct Polymarket access is filtered on the current local network. Production must use a legally permitted, unrestricted deployment region; do not use relays or geoblock bypasses.

### StatsBomb Open Data

- Repository: https://github.com/statsbomb/open-data

Free high-quality event/xG data for selected competitions and seasons. It does not provide complete recent two-season coverage for all six target competitions, so it is a research supplement rather than an operational feed.

### Tennis-Data.co.uk

- Homepage: http://www.tennis-data.co.uk/
- Data: http://www.tennis-data.co.uk/data.php
- Fields: http://www.tennis-data.co.uk/notes.txt

Verified advertised data:

- ATP results from 2000;
- WTA results/odds from 2007;
- surface and indoor/outdoor fields;
- winner/loser ranking at tournament start;
- retirement/walkover comments;
- historical pre-match and average/maximum odds;
- updated weekly, with Grand Slam delay.

It is batch historical data, not an operational schedule API. The site advertises free files but retains copyright over spreadsheet data. Obtain permission before using it in a commercial or paid alert service.

### API-Tennis trial

- Product/pricing: https://api-tennis.com/
- Documentation: https://api-tennis.com/documentation
- Terms: https://api-tennis.com/terms-of-use

All plans advertise a 14-day trial. There is no verified permanent free plan.

## 3. Paid operational candidates

### The Odds API paid

Verified current pricing:

- 20K credits: US$30/month;
- 100K: US$59/month;
- 5M: US$119/month;
- 15M: US$249/month.

Historical featured-market snapshots exist from June 2020, initially at 10-minute and later 5-minute intervals. Historical endpoints return the nearest snapshot at or before a requested timestamp, which fits report-time backtesting better than closing lines alone.

Official terms permit storage, application display, derived calculations, analytics, and ML training, while prohibiting raw-feed resale. This is a strong fit for derived Telegram alerts. Quotes remain indicative and should be manually verified before any wager.

Historical queries consume significant credits, so estimate a two-season backfill before choosing a plan.

### API-Tennis Starter

Verified current advertised terms:

- US$40/month;
- 8,000 requests/day;
- 14-day trial;
- fixtures, rankings, players, H2H/recent matches, surface, draw, odds, scores, and statistics;
- official documentation shows 1xBet in a match-winner response.

BC.Game is not documented. Historical retention, odds timestamps, withdrawal/status taxonomy, exact 500+ classification, and Telegram-derived-alert rights must be confirmed during the trial and in writing.

### Sportmonks Football

Official URLs:

- Coverage: https://www.sportmonks.com/football-api/coverage/
- Pricing: https://www.sportmonks.com/football-api/plans-pricing/
- Documentation: https://docs.sportmonks.com/v3

Verified official coverage lists all six target competitions with fixtures, historical data, match statistics, confirmed lineups/player statistics, and odds flags.

Advertised monthly plans:

- Starter: €29/month, choose 5 leagues;
- Growth: €99/month, choose 30 leagues;
- Pro: €249/month, choose 120 leagues;
- 14-day trial advertised;
- prices exclude VAT.

All six competitions exceed Starter’s five-league allowance unless an extra league can be added economically.

Relevant add-ons/bundles:

- xG & Pressure Index: official pages show varying starting packaging (€15 on one product page; €29 monthly/€24 annual equivalent on the plans page);
- Odds & Predictions: starting around €24 monthly/€15 annual equivalent;
- expected lineups: €199/month and only on Growth/Pro.

Do not purchase expected lineups for V1. Use confirmed lineups/injuries and downgrade data quality before team sheets are released.

### Sportradar Tennis

- Marketplace: https://marketplace.sportradar.com/products/6501e20f236aba44b550bdae
- Documentation: https://developer.sportradar.com/tennis/llms.txt

Strongest verified tennis lifecycle/status option. It covers Grand Slams, ATP/WTA, rankings, surfaces, H2H, historical seasons, and explicit cancelled/walkover/retired/defaulted states. Production pricing is quote-based and sportsbook odds are a separate commercial product.

### OpticOdds

- Documentation: https://developer.opticodds.com/reference/getting-started
- Historical product: https://opticodds.com/historical-odds

Commercial option with soccer/tennis, current and historical normalized sportsbook odds, streaming, and quoted limits. No simple free production key was verified.

## 4. Bookmaker-specific decision

### 1xBet

No public official self-service sportsbook odds API was verified. Use a licensed aggregator. The Odds API explicitly lists 1xBet in its EU bookmaker coverage; API-Tennis also documents it in tennis odds examples.

### BC.Game

No public official odds API was verified. BC.Game sportsbook terms prohibit automated systems including scanners and robots. Do not scrape or reverse-engineer private endpoints. Exclude direct BC.Game integration unless written permission or a licensed feed with clear rights is obtained.

Odds-API.io’s public bookmaker catalogue listed BC.Game, but exact plan availability, history, market coverage, and licensing remain unproven; documentation/catalogue presence alone is not enough for production selection.

## 5. Required proof gates

Before enabling model-backed alerts, trial/API responses must prove:

1. Every covered competition/tournament and V1 market is available.
2. Historical timestamps match the simulated daily decision time rather than only closing lines.
3. Two completed seasons/years are accessible and affordable.
4. 1xBet coverage is adequate; BC.Game is optional unless licensed.
5. Football xG/lineup/injury fields and missingness are understood.
6. Tennis ranking effective dates, surface, main-draw level, cancellation/retirement, and absence logic are reliable.
7. Terms permit storage, model training, derived Telegram alerts, and displayed indicative odds.
8. Polling volume fits the selected quota.

No provider adapter should be declared production-ready from documentation alone.
