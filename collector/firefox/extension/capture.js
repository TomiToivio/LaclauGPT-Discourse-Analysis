/**
 * LaclauGPT Brazil Collector — Firefox capture layer.
 *
 * LaclauGPT-native network capture based on the historical 2024
 * LaclauGPT TikTok Scraper: intercept relevant public platform API
 * responses, copy the response body to the local collector backend,
 * and leave the website's own response stream unchanged.
 *
 * Academic research use only.
 */

(() => {
  "use strict";

  const BACKEND_URL = "http://127.0.0.1:8765";

  // Request URL matchers per platform. Match endpoint families, never
  // deployment-specific GraphQL query IDs.
  const MATCHERS = {
    tiktok: /api\.tiktokv\.com|\/api\/post\/item_list|\/api\/search\/(?:item_list|general\/full)|\/api\/preload\/item_list/,
    instagram: /\/api\/v1\/|\/graphql(?:\/query)?(?:[/?]|$)/,
    x: /\/i\/api\/graphql(?:\/|\?|$)/,
  };

  function platformFor(url) {
    for (const [platform, matcher] of Object.entries(MATCHERS)) {
      if (matcher.test(url || "")) return platform;
    }
    return null;
  }

  async function tabUrlFor(tabId) {
    if (tabId < 0) return "";
    try {
      const tab = await browser.tabs.get(tabId);
      return tab?.url || "";
    } catch {
      return "";
    }
  }

  async function sendCapture(details, platform, body) {
    if (!body) return;
    const platformUrl = await tabUrlFor(details.tabId);
    try {
      const response = await fetch(`${BACKEND_URL}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          api_url: details.url,
          platform_url: platformUrl,
          captured_at: new Date().toISOString(),
          body,
        }),
      });
      if (!response.ok) {
        console.warn(
          "[laclaugpt-collector] backend rejected capture",
          platform,
          response.status,
          details.url,
        );
      }
    } catch (error) {
      console.warn("[laclaugpt-collector] backend unavailable", error);
    }
  }

  function captureResponse(details) {
    const platform = platformFor(details.url);
    if (!platform || ["HEAD", "OPTIONS"].includes(details.method)) return;

    let filter;
    try {
      filter = browser.webRequest.filterResponseData(details.requestId);
    } catch (error) {
      console.warn("[laclaugpt-collector] cannot attach response filter", details.url, error);
      return;
    }

    const decoder = new TextDecoder("utf-8");
    const chunks = [];

    filter.ondata = event => {
      // Keep a decoded private copy for LaclauGPT, but forward the original
      // bytes byte-for-byte. A StreamFilter must write or disconnect the
      // response or Firefox keeps the request open without delivering it.
      chunks.push(decoder.decode(event.data, { stream: true }));
      filter.write(event.data);
    };

    filter.onerror = event => {
      console.warn(
        "[laclaugpt-collector] response filter error",
        platform,
        details.url,
        event.error,
      );
      try { filter.disconnect(); } catch {}
    };

    filter.onstop = async () => {
      chunks.push(decoder.decode());
      // All bytes have already been forwarded in ondata. close() finishes the
      // filtered stream cleanly without changing the website response.
      try { filter.close(); } catch {}
      await sendCapture(details, platform, chunks.join(""));
    };
  }

  browser.webRequest.onHeadersReceived.addListener(
    captureResponse,
    {
      urls: ["<all_urls>"],
      types: ["xmlhttprequest"],
    },
    ["blocking"],
  );

  // Keep the backend status fresh without generating collector captures.
  setInterval(() => {
    fetch(`${BACKEND_URL}/ping`, { method: "POST" }).catch(() => {});
  }, 60000);
})();
