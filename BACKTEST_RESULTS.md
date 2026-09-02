# V1 Backtest Results

## Status

This document records chronological engineering validation for the frozen V1 probability policy. It does not make profitability, expected-value, or betting-return claims.

Football uses no bookmaker prices. Tennis historical probability validation is separate from the forward Polymarket executable-price validation still required before tennis alerts can be enabled.

## Football methodology

Data: 3,270 football-data.org matches from the five enabled competitions across the 2024/25 and 2025/26 seasons.

The feature builder uses only prior UTC dates. Each expanding-window fold has three non-overlapping stages:

1. fit the Poisson goal model on all observations before the calibration period;
2. calibrate 1X2, total 2.5, and BTTS probabilities on the later calibration period;
3. evaluate qualified forecasts on the subsequent evaluation period.

Evaluation windows do not overlap:

| Fold | Train before | Calibration | Evaluation | Evaluation matches |
|---|---|---|---|---:|
| F1 | 2025-01-01 | 2025-01-01 to 2025-02-28 | 2025-03-01 to 2025-05-31 | 484 |
| F2 | 2025-03-01 | 2025-03-01 to 2025-07-31 | 2025-08-01 to 2025-11-30 | 613 |
| F3 | 2025-08-01 | 2025-08-01 to 2025-11-30 | 2025-12-01 to 2026-02-28 | 562 |
| F4 | 2025-12-01 | 2025-12-01 to 2026-02-28 | 2026-03-01 to 2026-05-31 | 460 |

The periods were inspected during model development, so these are rolling out-of-sample engineering diagnostics rather than an untouched research holdout.

## Football threshold comparison

Pooled across the four evaluation windows:

| Probability floor | Market | Selections | Hit rate | 95% Wilson interval | Brier | Log loss | ECE |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0.60 | 1X2 | 296 | 71.28% | 65.88%–76.14% | 0.2044 | 0.6048 | 0.0603 |
| 0.60 | Total 2.5 | 294 | 67.35% | 61.79%–72.45% | 0.2195 | 0.6306 | 0.0312 |
| 0.60 | BTTS | 110 | 59.09% | 49.75%–67.82% | 0.2418 | 0.6766 | 0.0439 |
| 0.65 | 1X2 | 175 | 79.43% | 72.84%–84.75% | 0.1802 | 0.5584 | 0.1214 |
| 0.65 | Total 2.5 | 110 | 71.82% | 62.79%–79.38% | 0.2045 | 0.5993 | 0.0394 |
| 0.65 | BTTS | 30 | 60.00% | 42.32%–75.41% | 0.2414 | 0.6757 | 0.0834 |
| 0.70 | 1X2 | 91 | 78.02% | 68.48%–85.30% | 0.1868 | 0.5812 | 0.1075 |
| 0.70 | Total 2.5 | 24 | 70.83% | 50.83%–85.09% | 0.2032 | 0.5952 | 0.0117 |
| 0.70 | BTTS | 8 | 62.50% | 30.57%–86.32% | 0.2387 | 0.6713 | 0.0819 |

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

No Telegram sending, scheduler, automatic betting, wallet signing, deposits, withdrawals, or stakes are enabled by this validation.
