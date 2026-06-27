// SectorPulse Telegram status bot — Cloudflare Worker (single file, no build step).
// Answers /status, /sectors, /sector <TICKER>, /help by reading the live latest.json.
//
// Required Worker Variables (Settings -> Variables and Secrets):
//   BOT_TOKEN        (secret) Telegram bot token
//   WEBHOOK_SECRET   (secret) random string; must match the Telegram webhook secret_token
//   ALLOWED_CHAT_ID  (plain)  your chat id, so only you can query (optional but recommended)
//   DATA_URL         (plain)  optional override of the latest.json URL

const DEFAULT_DATA_URL =
  "https://raw.githubusercontent.com/NoamMarks/SectorPulse/data/latest.json";
const SITE = "https://noammarks.github.io/SectorPulse/";

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("SectorPulse bot is running.", { status: 200 });
    }
    // Verify the request really came from Telegram.
    if (env.WEBHOOK_SECRET &&
        request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("forbidden", { status: 403 });
    }

    let update;
    try { update = await request.json(); } catch { return ok(); }
    const msg = update.message || update.edited_message;
    if (!msg || !msg.text) return ok();

    const chatId = msg.chat.id;
    if (env.ALLOWED_CHAT_ID && String(chatId) !== String(env.ALLOWED_CHAT_ID)) {
      await send(env, chatId, "⛔ Not authorized.");
      return ok();
    }

    let reply;
    try {
      reply = await handle(msg.text, env);
    } catch (e) {
      reply = "⚠️ Couldn't read SectorPulse data right now — try again shortly.";
    }
    await send(env, chatId, reply);
    return ok();
  },
};

const ok = () => new Response("ok", { status: 200 });

async function handle(text, env) {
  const parts = text.trim().split(/\s+/);
  const name = parts[0].toLowerCase().replace(/@.*$/, ""); // strip /cmd@BotName
  const arg = (parts[1] || "").toUpperCase();

  if (name === "/help" || name === "/start") return helpText();

  const d = await fetchData(env); // only fetch when a data command is used

  if (name === "/status") return statusText(d);
  if (name === "/sectors") return sectorsText(d);
  if (name === "/sector") return arg ? sectorDetail(d, arg) : "Usage: <code>/sector XLK</code>";
  return "Unknown command.\n\n" + helpText();
}

async function fetchData(env) {
  const url = (env.DATA_URL || DEFAULT_DATA_URL) + "?t=" + Date.now();
  const r = await fetch(url, { cf: { cacheTtl: 0 }, headers: { "cache-control": "no-cache" } });
  if (!r.ok) throw new Error("data " + r.status);
  return await r.json();
}

function freshness(d) {
  return d.status === "intraday" || d.intraday ? "🟢 LIVE (provisional)" : "settled";
}

function fmt(x) {
  return x == null ? "—" : (x >= 0 ? "+" : "") + Number(x).toFixed(3);
}

function statusText(d) {
  const r = d.regime;
  const top = d.sectors.slice(0, 3).map((s, i) => `${i + 1}. ${s.ticker} (#${s.rss_rank})`).join("  ");
  const bo = d.sectors.filter((s) => s.breakout).map((s) => s.ticker);
  const rally = d.sectors.filter((s) => s.rally_flag).map((s) => s.ticker);
  const div = d.sectors.filter((s) => s.breadth_divergence).map((s) => s.ticker);
  const lines = [
    `📊 <b>SectorPulse</b> — ${d.as_of_trading_date} · ${freshness(d)}`,
    `Regime: <b>${r.state}</b> (${r.pct_sectors_above_200sma}% &gt; 200-DMA)`,
    `Top: ${top}`,
  ];
  if (bo.length) lines.push(`🚀 Breakouts: ${bo.join(", ")}`);
  if (rally.length) lines.push(`💪 Rally: ${rally.join(", ")}`);
  if (div.length) lines.push(`⚠️ Divergence: ${div.join(", ")}`);
  lines.push(`<a href="${SITE}">Open dashboard</a>`);
  return lines.join("\n");
}

function sectorsText(d) {
  const rows = d.sectors.map(
    (s, i) =>
      `${String(i + 1).padStart(2)}. <b>${s.ticker}</b> #${s.rss_rank}  rss ${fmt(s.rss)}  ` +
      `MAP ${Math.round(s.map_50)}%${s.breakout ? " 🚀" : ""}`
  );
  return `📊 <b>Leaderboard</b> — ${d.as_of_trading_date} · ${freshness(d)}\n` + rows.join("\n");
}

function sectorDetail(d, tk) {
  const s = d.sectors.find((x) => x.ticker === tk);
  if (!s) return `No sector "<b>${tk}</b>". Try /sectors.`;
  const lead = (s.leaders || []).map((h) => h.ticker).join(", ") || "none";
  const setup = (s.setups || []).map((h) => h.ticker).join(", ") || "none";
  const flags = [
    s.breakout ? "breakout" : null,
    s.rally_flag ? "rally" : null,
    s.breadth_divergence ? "⚠️ divergence" : null,
  ].filter(Boolean).join(" · ") || "none";
  return [
    `<b>${s.ticker}</b> — ${s.name}  (rank ${s.rss_rank})`,
    `RSS ${fmt(s.rss)} · MAP50 ${Math.round(s.map_50)}% (${s.map_band}) · trend ${s.trend}`,
    `Flags: ${flags}`,
    `Leaders (${(s.leaders || []).length}): ${lead}`,
    `Setups (${(s.setups || []).length}): ${setup}`,
  ].join("\n");
}

function helpText() {
  return [
    "🤖 <b>SectorPulse bot</b>",
    "/status — regime, top sectors, flags",
    "/sectors — full 11-sector leaderboard",
    "/sector XLK — one sector's detail + holdings",
    "/help — this message",
  ].join("\n");
}

async function send(env, chatId, text) {
  await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId, text, parse_mode: "HTML", disable_web_page_preview: true,
    }),
  });
}
