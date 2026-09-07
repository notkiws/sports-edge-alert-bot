# V1 Backtest Results

## Status

This document records chronological engineering validation for the frozen V1 probability policy. It does not make profitability, expected-value, or betting-return claims.

Football uses no bookmaker prices. Tennis historical probability validation is separate from the forward Polymarket executable-price validation still required before tennis alerts can be enabled.

## Football methodology

Data: 4,491 completed, scored football-data.org matches from the seven enabled
competitions across the 2024/25 and 2025/26 seasons. Bundesliga contributed 611
matches and Ligue 1 contributed 610.

The feature builder uses only prior UTC dates. Each expanding-window fold has three non-overlapping stages:

1. fit the Poisson goal model on all observations before the calibration period;
2. calibrate 1X2, total 2.5, and BTTS probabilities on the later calibration period;
3. evaluate qualified forecasts on the subsequent evaluation period.

Evaluation windows do not overlap:

| Fold | Train before | Calibration | Evaluation | Evaluation matches |
|---|---|---|---|---:|
| F1 | 2025-01-01 | 2025-01-01 to 2025-02-28 | 2025-03-01 to 2025-05-31 | 679 |
| F2 | 2025-03-01 | 2025-03-01 to 2025-07-31 | 2025-08-01 to 2025-11-30 | 847 |
| F3 | 2025-08-01 | 2025-08-01 to 2025-11-30 | 2025-12-01 to 2026-02-28 | 751 |
| F4 | 2025-12-01 | 2025-12-01 to 2026-02-28 | 2026-03-01 to 2026-05-31 | 648 |

The periods were inspected during model development, so these are rolling out-of-sample engineering diagnostics rather than an untouched research holdout.

## Football threshold comparison

Pooled across the four evaluation windows:

| Probability floor | Market | Selections | Hit rate | 95% Wilson interval | Brier | Log loss | ECE |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0.60 | 1X2 | 447 | 71.14% | 66.77%–75.15% | 0.2073 | 0.6105 | 0.0593 |
| 0.60 | Total 2.5 | 476 | 67.65% | 63.32%–71.69% | 0.2165 | 0.6244 | 0.0308 |
| 0.65 | 1X2 | 247 | 75.71% | 69.99%–80.64% | 0.1920 | 0.5828 | 0.0808 |
| 0.65 | Total 2.5 | 188 | 74.47% | 67.79%–80.17% | 0.1941 | 0.5776 | 0.0584 |
| 0.70 | 1X2 | 133 | 75.94% | 68.01%–82.41% | 0.1943 | 0.5959 | 0.0819 |
| 0.70 | Total 2.5 | 55 | 74.55% | 61.70%–84.19% | 0.1922 | 0.5734 | 0.0227 |

### Bundesliga and Ligue 1 activation gate

At the frozen 0.60 floor, evaluated independently within the pooled seven-league
expansion model:

| Competition | Market | Selections | Hit rate | 95% Wilson interval | Brier | Log loss | ECE |
|---|---|---:|---:|---:|---:|---:|---:|
| Bundesliga | 1X2 | 70 | 78.57% | 67.61%–86.56% | 0.1948 | 0.5911 | 0.1786 |
| Bundesliga | Total 2.5 | 86 | 67.44% | 56.98%–76.41% | 0.2084 | 0.6057 | 0.0292 |
| Ligue 1 | 1X2 | 62 | 62.90% | 50.46%–73.84% | 0.2303 | 0.6520 | 0.0436 |
| Ligue 1 | Total 2.5 | 53 | 71.70% | 58.43%–82.03% | 0.2102 | 0.6119 | 0.0943 |

All four competition-market aggregates exceed the frozen 0.60 realized-rate gate,
so `BL1` and `FL1` are enabled. Ligue 1 1X2 is the weakest result and has a broad
interval; its alert displays the exact 62.90% / n=62 historical evidence rather than
the pooled seven-league statistic.

### Expansion isolation

The original five-competition strategy remains frozen. Its model fitting,
calibration, rolling-form features, threshold, market allowlist, and historical
evidence use only `PL`, `PD`, `SA`, `DED`, and `CL`, exactly as before this expansion.

Only Bundesliga and Ligue 1 fixtures use the validated seven-league expansion model.
This also prevents new domestic history for Bundesliga/Ligue 1 clubs from changing
Champions League features in the legacy path. A regression run compared 29 current
legacy selections against commit `7ddfb4d`; every selection, probability, grade, and
historical-evidence field matched exactly.

### Frozen football policy

- Probability floor: `0.60`.
- Enabled pooled markets: `1X2`, `TOTAL_2_5`.
- Disabled: `BTTS` because its realized rate did not support the 0.60 label.
- Disabled pending implementation and separate validation: double chance, draw no bet, Asian handicap, team total, first-half result, and first-half total.
- At most three independently qualifying options may be displayed per match. The current allowlist can produce at most two.
- Football output remains probability-only, without odds, edge, EV, ROI, or staking language.

The 0.65 and 0.70 floors reduce coverage and do not provide sufficiently stable per-fold sample sizes to replace the strategy's specified 0.60 minimum globally.

## Team-regime weighting

The model accepts per-sample weights, and point-in-time regime entities distinguish effective and recorded timestamps. No reliable source-dated manager/squad transition registry is populated yet, so candidate values `0.25`, `0.50`, and `0.75` cannot be honestly distinguished from these data.

Frozen behavior until such a registry exists:

- pre-change fallback weight: `0.50`;
- unknown change: no inferred transition and weight `1.00`;
- no fabricated manager or squad-change dates.

## Tennis probability diagnostic

The leakage-safe tennis model was trained before 2024-09-01, calibrated through 2024-12-31, and evaluated on 3,461 matches from 2025. The probability ≥0.65/top-50 subset contained 1,523 matches, hit 75.64%, and had a 95% Wilson interval of 73.42%–77.73%, Brier score 0.1828, and log loss 0.5628.

This does not validate executable Polymarket edge. Tennis alerts remain disabled until forward snapshots provide exact match-contract mapping, target-size CLOB asks, spread/depth, fees, slippage, staleness, and at least 50 observations in the applicable edge bucket.

## Operational gate

Football Telegram delivery is enabled only for frozen-policy selections after its
separate controlled transport test. Automatic betting, wallet signing, deposits,
withdrawals, and staking remain absent.
