/**
 * LaclauGPT Social Media Collector — background service worker.
 *
 * Origin: adapted from TWO upstream sources (see README for full attribution):
 *  1. Zeeschuimer (digitalmethodsinitiative, MIT) — the network-interception
 *     approach: platform API responses are read off the wire via
 *     browser.webRequest.filterResponseData, forwarded to per-platform
 *     parsers, and buffered for export. No DOM scraping.
 *  2. The historical LaclauGPT-TikTok-Scraper (CC0, 2024): the same
 *     filterResponseData technique, extended here from TikTok-only to
 *     TikTok + Instagram + X.
 *
 * Re-implemented for LaclauGPT (issue #20) — no verbatim upstream code.
 * License: MIT (this file), upstream licenses respected.
 */

// ── platform modules: endpoint detection + parsing ────────────────────
import { parse as parseTikTok } from "./modules/tiktok.js";
import { parse as parseInstagram } from "./modules/instagram.js";
import { parse as parseX } from "./modules/twitter.js";

const PARSERS = [
  { match: /tiktok\.com/i, name: "tiktok", fn: parseTikTok },
  { match: /instagram\.com/i, name: "instagram", fn: parseInstagram },
  { match: /(twitter|x)\.com/i, name: "x", fn: parseX },
];

// ── capture buffer (per platform) ─────────────────────────────────────
// Records sit in browser.storage.local until the scheduler drains them.
// Keyed by platform; each record = one normalised post + provenance.
let BUFFER = { tiktok: [], instagram: [], x: [] };
const MAX_BUFFER = 5000; // per platform; oldest dropped (storage.local cap safety)

function bufferRecord(platform, record) {
  if (!PARSERS[platform] && !["tiktok", "instagram", "x"].includes(platform)) return;
  record.collector_version = "laclaugpt-collector-0.1.0";
  record.captured_at = new Date().toISOString();
  BUFFER[platform].push(record);
  if (BUFFER[platform].length > MAX_BUFFER) {
    BUFFER[platform] = BUFFER[platform].slice(-MAX_BUFFER);
  }
  browser.storage.local.set({ ["buffer_" + platform]: BUFFER[platform] });
}

// ── webRequest interception (Zeeschuimer technique) ───────────────────
function listener(details) {
  // find which platform parser owns this URL
  const parser = PARSERS.find(p => p.match.test(details.url));
  if (!parser) return;

  const filter = browser.webRequest.filterResponseData(details.requestId);
  const decoder = new TextDecoder("utf-8");
  const encoder = new TextEncoder();
  let responseData = "";

  filter.ondata = (event) => {
    responseData += decoder.decode(event.data, { stream: true });
    filter.write(encoder.encode(event.data));   // forward untouched
  };

  filter.onstop = async () => {
    filter.disconnect();
    try {
      const records = await parser.fn(responseData, details.url, details.originUrl || details.documentUrl || "");
      for (const rec of records) {
        bufferRecord(parser.name, {
          platform: parser.name,
          post_id: String(rec.post_id),          // X ids: ALWAYS exact strings
          author: rec.author ?? null,
          author_display: rec.author_display ?? null,
          timestamp: rec.timestamp ?? null,
          url: rec.url ?? null,
          text: rec.text ?? rec.body ?? null,
          hashtags: rec.hashtags ?? [],
          engagement: rec.engagement ?? {},
          media_urls: rec.media_urls ?? [],
          raw_ref: null,                          // raw payload kept separately below
          source_response: details.url,
        });
      }
    } catch (e) {
      console.warn("[laclaugpt-collector] parse error", parser.name, e);
    }
  };
}

browser.webRequest.onHeadersReceived.addListener(
  listener,
  { urls: ["*://*.tiktok.com/*", "*://*.instagram.com/*", "*://*.x.com/*", "*://*.twitter.com/*"] },
  ["blocking"]
);

// ── message API: content script + scheduler handshake ────────────────
browser.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg?.type === "get_buffer") {
    const platform = msg.platform;
    const items = BUFFER[platform] || [];
    BUFFER[platform] = [];                       // drain after fetch
    browser.storage.local.set({ ["buffer_" + platform]: [] });
    return { platform, items, count: items.length };
  }
  if (msg?.type === "buffer_status") {
    return Object.fromEntries(Object.entries(BUFFER).map(([k, v]) => [k, v.length]));
  }
  return null;
});

// restore persisted buffers on startup
(async () => {
  for (const platform of Object.keys(BUFFER)) {
    const stored = await browser.storage.local.get("buffer_" + platform);
    if (Array.isArray(stored["buffer_" + platform])) {
      BUFFER[platform] = stored["buffer_" + platform];
    }
  }
})();