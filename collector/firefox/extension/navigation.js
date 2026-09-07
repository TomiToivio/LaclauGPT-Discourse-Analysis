/**
 * LaclauGPT Brazil Collector — tour navigation layer.
 *
 * Adapted from the historical LaclauGPT TikTok Scraper content-script
 * navigation (CC0 1.0) — but modernised: instead of a random-walk
 * content script, the backend hands the extension a deterministic tour
 * (account list from the study config) and the extension visits each
 * account page, scrolling to trigger pagination, then moves on.
 *
 * Academic research use only.
 */

const BACKEND = "http://127.0.0.1:8765";

const BASE_URLS = {
  tiktok: ["https://www.tiktok.com/@{handle}"],
  instagram: ["https://www.instagram.com/{handle}/", "https://www.instagram.com/{handle}/reels/"],
  x: ["https://x.com/{handle}", "https://x.com/{handle}/with_replies"],
};

let tour = null;        // {accounts: [{name, kind, platform, handle}], index}
let currentTabId = null;
let busy = false;

async function fetchTour() {
  try {
    const r = await fetch(`${BACKEND}/tour`);
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    return null;
  }
}

function pageUrl(item) {
  const templates = BASE_URLS[item.platform] || [];
  const tpl = templates[0] || "";
  return tpl.replace("{handle}", item.handle);
}

async function visitNext() {
  if (busy) return;
  if (!tour) tour = await fetchTour();
  if (!tour || !tour.accounts || !tour.accounts.length) return;

  const item = tour.accounts[tour.index % tour.accounts.length];
  tour.index += 1;
  busy = true;

  const url = pageUrl(item);
  try {
    const tab = await browser.tabs.create({ url, active: true });
    currentTabId = tab.id;

    // scroll several times over ~30s to trigger lazy loading, then close
    let scrolls = 0;
    const timer = setInterval(async () => {
      scrolls += 1;
      try {
        await browser.tabs.sendMessage(tab.id, { action: "scroll" });
      } catch (e) {
        // content script not injected (e.g. login page) — carry on
      }
      if (scrolls >= 10) {
        clearInterval(timer);
        try { await browser.tabs.remove(tab.id); } catch (e) {}
        busy = false;
      }
    }, 3000);
  } catch (e) {
    busy = false;
  }
}

// main loop: ask the backend for a tour every 5 minutes; the backend
// decides whether this is the right time of day to collect
setInterval(visitNext, 300000);
visitNext();