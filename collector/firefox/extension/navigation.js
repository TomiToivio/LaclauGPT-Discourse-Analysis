/**
 * LaclauGPT Brazil Collector — tour navigation layer.
 *
 * The backend owns the study configuration and returns one navigation row per
 * configured account/page URL. This script refreshes that tour before every
 * visit so study-window changes and config edits take effect without reloading
 * the extension.
 *
 * Academic research use only.
 */

(() => {
  "use strict";

  const BACKEND_URL = "http://100.64.0.10:8765";
  const VISIT_INTERVAL_MS = 300000;
  const SCROLL_INTERVAL_MS = 3000;
  const SCROLLS_PER_VISIT = 10;

  let nextIndex = 0;
  let currentTabId = null;
  let busy = false;

  async function fetchTour() {
    try {
      const response = await fetch(`${BACKEND_URL}/tour`, { cache: "no-store" });
      if (!response.ok) return null;
      return await response.json();
    } catch {
      return null;
    }
  }

  async function closeCurrentTab(tabId) {
    try { await browser.tabs.remove(tabId); } catch {}
    if (currentTabId === tabId) currentTabId = null;
  }

  async function visitNext() {
    if (busy) return;

    // Refresh on every cycle. Once the backend says the study is inactive,
    // automatic navigation stops immediately even if the extension has been
    // running for days.
    const tour = await fetchTour();
    const accounts = Array.isArray(tour?.accounts) ? tour.accounts : [];
    if (!tour?.active || accounts.length === 0) return;

    const item = accounts[nextIndex % accounts.length];
    nextIndex = (nextIndex + 1) % accounts.length;
    const url = item?.url;
    if (!url) return;

    busy = true;
    try {
      const tab = await browser.tabs.create({ url, active: true });
      currentTabId = tab.id;

      let scrolls = 0;
      const timer = setInterval(async () => {
        scrolls += 1;
        try {
          await browser.tabs.sendMessage(tab.id, { action: "scroll" });
        } catch {
          // Login/consent pages may not have our content script yet. Keeping
          // the visit alive still lets the user resolve the page manually.
        }

        if (scrolls >= SCROLLS_PER_VISIT) {
          clearInterval(timer);
          await closeCurrentTab(tab.id);
          busy = false;
        }
      }, SCROLL_INTERVAL_MS);
    } catch (error) {
      console.warn("[laclaugpt-collector] navigation failed", item, error);
      currentTabId = null;
      busy = false;
    }
  }

  // If the extension is reloaded while one of its own tour tabs survives,
  // currentTabId is naturally lost; visits remain bounded to one new tab per
  // interval and the old tab is harmless.
  setInterval(visitNext, VISIT_INTERVAL_MS);
  visitNext();
})();
