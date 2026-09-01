# Data Source Evaluation

> Verification status: direct public documentation checks completed for the entries marked **verified**. Provider account/trial tests are still required before purchase or production use.

## 1. Current recommendation

### Primary odds feed: Odds-API.io

**Why it currently leads**

- Its public `/v3/bookmakers` endpoint returned both `1xbet` and `BC.Game` as active.
- Its public `/v3/sports` endpoint returned both Football and Tennis.
- Documentation exposes current odds, multi-event odds, recently updated odds, movement history, historical events/odds, and bulk historical closing lines.
- It provides a single normalization surface instead of scraping bookmaker sites.

**Directly verified URLs**

- Documentation: https://docs.odds-api.io/
- Documentation index: https://docs.odds-api.io/llms.txt
- Bookmakers: https://api.odds-api.io/v3/bookmakers
- Sports: https://api.odds-api.io/v3/sports
- Pricing: https://odds-api.io/pricing

**Directly observed public catalogue entries**

```json
{"name": "1xbet", "active": true}
{"name": "BC.Game", "active": true}
```

**Observed public pricing page**

- Solo: £49/month, 2 bookmakers, 5,000 requests/hour.
- Starter: £99/month, 5 bookmakers, 5,000 requests/hour.
- Growth: £179/month, 10 bookmakers, 5,000 requests/hour.
- Pro: £229/month, 15 bookmakers, 5,000 requests/hour.
- The page states that new free API keys are paused indefinitely.

Prices and inclusions can change and must be rechecked before purchase.

**Unresolved gates**

- Whether the Solo tier allows choosing both 1xBet and BC.Game specifically.
- Exact football competition and V1 market coverage for those two books.
- Exact ATP/WTA tournament coverage.
- Cost/inclusion of two years of historical closing or timestamped odds.
- Whether report-time historical snapshots are available; closing odds alone are insufficient for an exact three-hours-before-earliest-event backtest.
- Telegram display/redistribution terms.

### Tennis statistics candidate: API-Tennis

**Directly verified URLs**

- Website/pricing section: https://api-tennis.com/#plans
- Documentation: https://api-tennis.com/documentation

**Verified documented capabilities**

- tournaments;
- fixtures and live scores;
- standings/rankings and players;
- H2H;
- pre-match odds and live odds;
- draws including tournament surface and qualification flags;
- documented sample odds containing 1xBet.

**Observed public pricing page**

- Starter: $40/month, 8,000 requests/day, 14-day trial.
- Premium: $60/month, 80,000 requests/day, 14-day trial.
- Business: $80/month, 200,000 requests/day, 14-day trial.
- Ultra: $120/month, 2,000,000 requests/day, 14-day trial.

The public page lists tournaments, fixtures, live score, standings, players, H2H, odds, and draw on Starter. Prices and inclusions must be rechecked at signup.

**Unresolved gates**

- Historical depth and effective-date ranking snapshots.
- Reliable representation of retirement/walkover/withdrawal and absence periods.
- Main-draw tournament-level taxonomy needed to enforce 500+.
- Serve/return statistics completeness.
- Data license and Telegram display terms.

### Football statistics candidate: Sportmonks Football API 3.0

**Directly verified URLs**

- Documentation: https://docs.sportmonks.com/v3
- Documentation index: https://docs.sportmonks.com/v3/llms.txt

**Verified documented capabilities**

- current and historical fixtures;
- date/range and H2H fixture endpoints;
- fixture statistics;
- lineups and predicted lineups;
- xG endpoints and coverage documentation;
- pre-match news;
- predictions/probabilities;
- standard and premium pre-match odds;
- premium historical odds endpoints;
- bookmaker and market endpoints.

**Unresolved gates**

- Current monthly price for the exact six competitions and required add-ons.
- xG coverage for every target competition and both historical seasons.
- injury/suspension coverage and expected-lineup timeliness.
- whether premium historical odds are included in an affordable plan.
- exact 1xBet/BC.Game availability if Sportmonks odds were used instead of Odds-API.io.
- redistribution rights.

### Optional market corroboration: Polymarket

Public, read-only APIs require no trading credentials:

- Gamma API: https://gamma-api.polymarket.com
- CLOB API: https://clob.polymarket.com
- Data API: https://data-api.polymarket.com

Use only for exact event/outcome matches. It is not a required feed because many football derivative markets and tennis matches may not have corresponding contracts.

## 2. Sources not selected as the primary design assumption

### Direct 1xBet/BC.Game website scraping

Do not make this the default architecture because:

- HTML and internal endpoints can change without notice;
- bot protection and regional behavior are likely;
- account/session flows could accidentally couple alerts to wagering credentials;
- terms may prohibit automated extraction;
- historical data and stable market IDs are difficult to guarantee.

A licensed aggregator with documented access is preferred.

### football-data.org

The public documentation verifies fixtures/results, teams, standings, match details, lineups fields, and basic 1X2 odds fields. It does not by itself establish all required xG, injury, historical-odds, Asian-line, BTTS, team-total, and first-half-market coverage. It may be useful as a low-cost schedule/result fallback, not yet as the complete V1 feed.

### The Odds API

Documentation verifies current and historical odds and tennis/football coverage. Its common markets are moneyline, spreads, and totals, with regional bookmaker lists. Exact 1xBet and BC.Game inclusion has not been verified, so it remains a fallback candidate rather than the current first choice.

## 3. Required provider proof before coding adapters

Obtain trial/API-key responses and save redacted samples for:

1. Premier League full-time 1X2, Asian handicap, totals, BTTS, team totals, first-half result, and first-half totals from 1xBet and BC.Game.
2. One match from each remaining football competition.
3. ATP and WTA 500/1000/Grand Slam match-winner odds from both target bookmakers where offered.
4. Historical odds snapshots or closing lines for all V1 market families.
5. Football xG, lineups, injuries/news, scores, and fixture-status changes.
6. Tennis ranking, surface, tournament level, main-draw flag, result status, retirement/walkover, and H2H.

No adapter should be declared production-ready from documentation alone.
