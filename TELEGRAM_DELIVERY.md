# Telegram Football Delivery

Telegram delivery is an alert-only last-mile transport. It does not contain wallet,
staking, signing, betting, or order-placement functionality.

## Safety defaults

Sending is disabled unless `TELEGRAM_SENDING_ENABLED=true` is present in the private
runtime environment. When disabled, the command exits before loading forecasts,
credentials, or opening a network connection.

Private runtime values (never commit them):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TELEGRAM_SENDING_ENABLED`

## Delivery behavior

`python -m sports_edge.commands.send_telegram_due` sends only batches inside the same
15-minute due window used by the WIB dry-run scheduler. Each qualified football
selection is rendered independently with the frozen concise bilingual renderer.

Confirmed deliveries are appended to the private ignored state file:

`artifacts/runtime/telegram-deliveries.jsonl`

A filesystem lock protects the check-and-send operation. The state is flushed and
synced only after Telegram returns a message ID. Repeated polling therefore skips a
confirmed delivery, while a failed request remains eligible for retry.

Network failures, HTTP 429 responses, and temporary 5xx responses receive at most two
retries. Errors never include the bot token.

## Production activation

Install the five-minute network-delivery cron only after the private credential setup,
controlled test send, destination verification, and explicit activation approval are
complete. The authoritative deployment completed those gates before enabling its
single delivery cron.

To pause delivery without removing credentials, set
`TELEGRAM_SENDING_ENABLED=false`. The command then exits before reading forecasts or
opening a network connection.
