# Sports Probability Alert Bot

Private, alert-only football and tennis pre-match analysis system. Football reports contain up to three calibrated ≥60% probability forecasts per qualifying match without evaluating bookmaker odds. Tennis alerts use an independent surface/form model and require statistically validated edge over an executable Polymarket CLOB ask.

## Safety boundary

This project does not place bets, connect wagering credentials, or recommend stakes.

## Current status

- V1 strategy frozen in [`STRATEGY.md`](STRATEGY.md).
- Architecture/provider gates documented in [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`DATA_SOURCES.md`](DATA_SOURCES.md).
- Provider trial responses and two-year report-time historical odds remain hard gates before production adapters/backtests.

## Local development

A clean Python 3.11 environment is required. This Mac currently uses `.venv/bin/python` created from Hermes' Python 3.11.15 executable because the shell-default Anaconda Python is 3.8.

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src
```
