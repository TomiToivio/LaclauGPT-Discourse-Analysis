/**
 * LaclauGPT Brazil Collector — Firefox capture layer.
 *
 * Adapted from the historical LaclauGPT TikTok Scraper Firefox extension
 * (CC0 1.0, github.com/TomiToivio/LaclauGPT-TikTok-Scraper) and the
 * capture architecture of Zeeschuimer (MPL-2.0,
 * github.com/digitalmethodsinitiative/zeeschuimer, Copyright Stijn
 * Peeters). Modified 2026 for the LaclauGPT Brazil 2026 study:
 *
 * - captures API response BODIES via webRequest.filterResponseData
 *   (Firefox-only API; this is why the collector runs on Firefox);
 * - POSTs each response to the local Python backend (collector/firefox/
 *   firefox_backend.py) which runs the tested Zeeschuimer-derived
 *   parsers and the durable store — the extension stays a thin capture
 *   layer with no parsing logic;
 * - platform matchers mirror collector/browser.py PLATFORM_API_MATCHERS.
 *
 * Academic research use only.
 */

const BACKEND = "http://127.0.0.1:8765";

// request URL matchers per platform (same patterns as the CDP driver)
const MATCHERS = {
  tiktok: /api\.tiktokv\.com|\/api\/post\/item_list|\/api\/search\/item_list|\/api\/preload\/item_list/,
  instagram: /\/api\/v1\/|\/graphql\/query/,
  x: /\/i\/api\/graphql/,
};

function platformFor(url) {
  for (const [platform, re] of Object.entries(MATCHERS)) {
    if (re.test(url)) return platform;
  }
  return null;
}

// ---- response body capture (the Firefox advantage) -------------------

browser.webRequest.onHeadersReceived.addListener(
  (details) => {
    const platform = platformFor(details.url);
    if (!platform || details.method !== "GET") return;

    const tabUrl = details.tabId >= 0
      ? browser.tabs.get(details.tabId).then(tab => tab.url).catch(() => "")
      : Promise.resolve("");

    const decoder = new TextDecoder("utf-8");
    const filter = browser.webRequest.filterResponseData(details.requestId);
    const chunks = [];

    filter.ondata = (event) => chunks.push(decoder.decode(event.data, { stream: true }));
    filter.onstop = async () => {
      filter.close();
      const body = chunks.join("");
      let tabUrlStr = "";
      try { tabUrlStr = await tabUrl; } catch (e) {}
      if (!body) return;
      // the backend parses (Zeeschuimer-derived modules) and stores;
      // the extension never interprets platform payloads itself
      fetch(`${BACKEND}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          api_url: details.url,
          platform_url: tabUrlStr,
          captured_at: new Date().toISOString(),
          body,
        }),
      }).catch(() => {}); // backend down: capture is best-effort
    };
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);

// keep the request log light: only report alive-ness to the backend
setInterval(() => {
  fetch(`${BACKEND}/ping`, { method: "POST" }).catch(() => {});
}, 60000);