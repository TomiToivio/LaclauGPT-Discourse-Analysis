/**
 * LaclauGPT Social Media Collector — Firefox background capture.
 *
 * This is the browser capture/orchestration layer of LaclauGPT. Its design
 * follows the original 2024 LaclauGPT-TikTok-Scraper: intercept relevant
 * browser responses, route them to platform-specific parsers, and persist
 * LaclauGPT-owned records for the local collector backend.
 *
 * Platform parsing lives in modules/tiktok.js, modules/instagram.js and
 * modules/twitter.js. background.js deliberately does not duplicate parser
 * code. Capture, parsing and storage remain separate concerns.
 *
 * Author: Tomi Toivio / LaclauGPT
 * License: CC0 1.0 Universal
 */

import { parse as parseTikTok } from "./modules/tiktok.js";
import { parse as parseInstagram } from "./modules/instagram.js";
import { parse as parseX } from "./modules/twitter.js";

const PARSERS = {
  tiktok: parseTikTok,
  instagram: parseInstagram,
  x: parseX,
};

const PLATFORMS = Object.freeze(Object.keys(PARSERS));
const MAX_BUFFER = 5000;
const COLLECTOR_VERSION = `laclaugpt-collector-${browser.runtime.getManifest().version}`;

let BUFFER = {
  tiktok: [],
  instagram: [],
  x: [],
};

function platformFromUrl(url) {
  if (!url || typeof url !== "string") return null;
  try {
    const host = new URL(url).hostname.toLowerCase().replace(/^www\./, "");
    if (host === "tiktok.com" || host.endsWith(".tiktok.com")) return "tiktok";
    if (host === "instagram.com" || host.endsWith(".instagram.com")) return "instagram";
    if (
      host === "x.com" || host.endsWith(".x.com") ||
      host === "twitter.com" || host.endsWith(".twitter.com")
    ) return "x";
  } catch {
    return null;
  }
  return null;
}

function unique(values) {
  return [...new Set((values ?? []).filter(Boolean))];
}

function mergeRecord(previous, incoming) {
  if (!previous) return incoming;
  return {
    ...previous,
    ...incoming,
    hashtags: unique([...(previous.hashtags ?? []), ...(incoming.hashtags ?? [])]),
    mentions: unique([...(previous.mentions ?? []), ...(incoming.mentions ?? [])]),
    urls: unique([...(previous.urls ?? []), ...(incoming.urls ?? [])]),
    media_urls: unique([...(previous.media_urls ?? []), ...(incoming.media_urls ?? [])]),
    engagement: {
      ...(previous.engagement ?? {}),
      ...(incoming.engagement ?? {}),
    },
  };
}

function recordForBuffer(platform, record, provenance = {}) {
  if (!record?.post_id) return null;
  return {
    ...record,
    platform,
    post_id: String(record.post_id),
    collector_version: COLLECTOR_VERSION,
    captured_at: new Date().toISOString(),
    capture_kind: provenance.kind ?? "network",
    source_response: provenance.requestUrl ?? record.source_response ?? null,
    source_page: provenance.pageUrl ?? record.source_page ?? null,
    raw_ref: record.raw_ref ?? null,
  };
}

async function persistPlatformBuffer(platform) {
  await browser.storage.local.set({ [`buffer_${platform}`]: BUFFER[platform] });
}

async function bufferRecord(platform, record, provenance = {}) {
  if (!PLATFORMS.includes(platform)) return false;
  const normalized = recordForBuffer(platform, record, provenance);
  if (!normalized) return false;

  const index = BUFFER[platform].findIndex(item => String(item.post_id) === normalized.post_id);
  if (index >= 0) {
    BUFFER[platform][index] = mergeRecord(BUFFER[platform][index], normalized);
  } else {
    BUFFER[platform].push(normalized);
  }

  if (BUFFER[platform].length > MAX_BUFFER) {
    BUFFER[platform] = BUFFER[platform].slice(-MAX_BUFFER);
  }

  await persistPlatformBuffer(platform);
  return true;
}

async function restoreBuffers() {
  for (const platform of PLATFORMS) {
    const stored = await browser.storage.local.get(`buffer_${platform}`);
    const value = stored[`buffer_${platform}`];
    if (Array.isArray(value)) BUFFER[platform] = value;
  }
}

const bufferReady = restoreBuffers().catch(error => {
  console.warn("[laclaugpt-collector] failed to restore capture buffers", error);
});

async function dataGrabber(platform, response, requestUrl, pageUrl, kind = "network") {
  const parser = PARSERS[platform];
  if (!parser) return 0;

  let records;
  try {
    records = await parser(response, requestUrl, pageUrl);
  } catch (error) {
    console.warn(`[laclaugpt-collector] ${platform} parser failed`, error);
    return 0;
  }

  if (!Array.isArray(records) || records.length === 0) return 0;

  await bufferReady;
  let accepted = 0;
  for (const record of records) {
    if (await bufferRecord(platform, record, { requestUrl, pageUrl, kind })) {
      accepted += 1;
    }
  }
  return accepted;
}

/**
 * Intercept a response without modifying what the website receives.
 *
 * The historical LaclauGPT scraper used filterResponseData for this job.
 * event.data is written back as the original ArrayBuffer, byte-for-byte;
 * decoding is only for LaclauGPT's private parser copy.
 */
function listener(details) {
  const platform = platformFromUrl(details.url);
  if (!platform) return;

  let filter;
  try {
    filter = browser.webRequest.filterResponseData(details.requestId);
  } catch (error) {
    console.warn("[laclaugpt-collector] cannot attach response filter", details.url, error);
    return;
  }

  const decoder = new TextDecoder("utf-8");
  let responseData = "";

  filter.ondata = event => {
    responseData += decoder.decode(event.data, { stream: true });
    // Forward exactly the bytes received by the browser. Do not decode and
    // re-encode the website response.
    filter.write(event.data);
  };

  filter.onerror = event => {
    console.warn("[laclaugpt-collector] response filter error", platform, details.url, event.error);
    try { filter.disconnect(); } catch {}
  };

  filter.onstop = async () => {
    responseData += decoder.decode();
    try { filter.disconnect(); } catch {}

    const pageUrl = details.documentUrl || details.originUrl || "";
    await dataGrabber(platform, responseData, details.url, pageUrl, "network");
  };
}

browser.webRequest.onHeadersReceived.addListener(
  listener,
  {
    urls: [
      "*://*.tiktok.com/*",
      "*://*.instagram.com/*",
      "*://*.x.com/*",
      "*://*.twitter.com/*",
    ],
    // Capture source HTML and API/GraphQL JSON, never image/video bodies.
    types: ["main_frame", "xmlhttprequest"],
  },
  ["blocking"],
);

browser.runtime.onMessage.addListener(async (message, sender) => {
  await bufferReady;

  // content.js sends embedded page JSON that never arrives as a separate XHR.
  if (message?.type === "embedded") {
    const platform = message.platform;
    if (!PLATFORMS.includes(platform) || !Array.isArray(message.payloads)) {
      return { accepted: 0 };
    }

    const pageUrl = sender?.tab?.url || message.page_url || "";
    let accepted = 0;
    for (const payload of message.payloads) {
      if (!payload?.json) continue;
      accepted += await dataGrabber(
        platform,
        payload.json,
        pageUrl,
        pageUrl,
        `embedded:${payload.kind || "json"}`,
      );
    }
    return { platform, accepted };
  }

  if (message?.type === "get_buffer") {
    const platform = message.platform;
    if (!PLATFORMS.includes(platform)) return { platform, items: [], count: 0 };

    const items = BUFFER[platform];
    BUFFER[platform] = [];
    await persistPlatformBuffer(platform);
    return { platform, items, count: items.length };
  }

  if (message?.type === "buffer_status") {
    return Object.fromEntries(PLATFORMS.map(platform => [platform, BUFFER[platform].length]));
  }

  if (message?.type === "clear_buffer") {
    const platforms = message.platform && PLATFORMS.includes(message.platform)
      ? [message.platform]
      : PLATFORMS;
    for (const platform of platforms) {
      BUFFER[platform] = [];
      await persistPlatformBuffer(platform);
    }
    return { cleared: platforms };
  }

  return null;
});
