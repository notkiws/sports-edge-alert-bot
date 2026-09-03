# Telegram Dry-Run Pipeline

Telegram delivery is intentionally disabled. This pipeline only writes plain-text preview files.

## Runtime input

The due-only scheduler looks for:

`artifacts/runtime/football-report-selections.json`

The file must contain a `football` array. Each selection includes competition, UTC kickoff, teams, enabled market, bilingual selection/reasoning/warning text, calibrated probability, historical hit rate/sample size, and quality grade.

The renderer independently filters out:

- probabilities below the frozen `0.60` football floor;
- markets outside the frozen allowlist (`1X2`, `TOTAL_2_5`).

## Preview all supplied days

```bash
.venv/bin/python -m sports_edge.commands.render_telegram_dry_run \
  --input artifacts/runtime/football-report-selections.json \
  --destination artifacts/telegram-dry-run
```

## Poll only currently due reports

```bash
.venv/bin/python -m sports_edge.commands.render_telegram_dry_run \
  --due-only \
  --input artifacts/runtime/football-report-selections.json \
  --destination artifacts/telegram-dry-run
```

A daily report becomes due three hours before the earliest covered event on its WIB calendar day. The polling window is 15 minutes. Existing daily artifacts are never overwritten.

## Safety

- No Telegram API client is present.
- No bot token is read.
- No network message is sent.
- No betting, wallet, staking, or execution behavior exists.
- Every artifact begins with `DRY RUN — NOT SENT` and `UJI COBA — TIDAK DIKIRIM`.
