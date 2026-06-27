# SectorPulse status bot (Cloudflare Worker)

An interactive Telegram bot: message it `/status` (or `/sectors`, `/sector XLK`, `/help`) any time and it replies by reading the live `latest.json`. Runs on Cloudflare's free tier — always on, instant, no credit card.

## Commands
| Command | Reply |
|---|---|
| `/status` | regime, top 3 sectors, breakouts/rally/divergence flags, freshness |
| `/sectors` | full 11-sector leaderboard |
| `/sector XLK` | one sector's RSS/MAP/flags + its Leaders & Setups |
| `/help` | command list |

## Setup (dashboard, ~5 min, no CLI)

1. Create a free **Cloudflare** account → **Workers & Pages** → **Create** → **Create Worker** → name it `sectorpulse-bot` → **Deploy** → **Edit code**.
2. Replace the sample code with the contents of [`worker.js`](worker.js) → **Deploy**.
3. **Settings → Variables and Secrets** → add:
   | Name | Type | Value |
   |---|---|---|
   | `BOT_TOKEN` | Secret | your Telegram bot token |
   | `WEBHOOK_SECRET` | Secret | the random string below |
   | `ALLOWED_CHAT_ID` | Text | `540648770` (only you can query) |
   | `DATA_URL` | Text | `https://raw.githubusercontent.com/NoamMarks/SectorPulse/data/latest.json` |

   Webhook secret (already generated for you):
   ```
   172ee283835d5e5d6474db25c9819204be5d94061b664d92
   ```
4. **Deploy** again so the variables take effect, and copy your Worker URL (looks like `https://sectorpulse-bot.<your-subdomain>.workers.dev`).
5. Send that URL back and I'll register the Telegram webhook (or do it yourself):
   ```
   curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=<WORKER_URL>&secret_token=172ee283835d5e5d6474db25c9819204be5d94061b664d92&allowed_updates=[\"message\"]"
   ```

Then message your bot `/status` — instant reply.

## CLI alternative
See the top of [`wrangler.toml`](wrangler.toml).
