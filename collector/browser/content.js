/**
 * LaclauGPT Social Media Collector — content script.
 *
 * Two jobs (both inherited from the historical LaclauGPT-TikTok-Scraper,
 * modernised for Manifest V3 and extended to three platforms):
 *  1. Extract EMBEDDED page data that never travels as XHR — TikTok serves
 *     SIGI_STATE / __UNIVERSAL_DATA_FOR_REHYDRATION__ blocks inline
 *     (Zeeschuimer's embedded-extraction idea).
 *  2. Periodically hand the background worker nothing — the network layer
 *     does the real capture; this script only adds embedded-JSON payloads
 *     the webRequest filter cannot see.
 */

function extractTikTokEmbedded() {
  // Zeeschuimer-style embedded state extraction (SIGI_STATE + UNIVERSAL_DATA)
  const out = [];
  const sigil = document.getElementById("SIGI_STATE");
  if (sigil) {
    try { out.push({ kind: "SIGI_STATE", json: JSON.parse(sigil.textContent) }); } catch (e) {}
  }
  const ud = document.getElementById("__UNIVERSAL_DATA_FOR_REHYDRATION__");
  if (ud) {
    try { out.push({ kind: "__UNIVERSAL_DATA_FOR_REHYDRATION__", json: JSON.parse(ud.textContent) }); } catch (e) {}
  }
  return out;
}

function extractInstagramEmbedded() {
  const out = [];
  for (const s of document.querySelectorAll("script[type='application/json']")) {
    const txt = s.textContent || "";
    if (txt.includes("xdt_api__v1__feed") || txt.includes("xdt_api__v1__user")) {
      try { out.push({ kind: "ig-embedded", json: JSON.parse(txt) }); } catch (e) {}
    }
  }
  return out;
}

function sendEmbedded(platform, payloads) {
  if (!payloads.length) return;
  browser.runtime.sendMessage({ type: "embedded", platform, payloads }).catch(() => {});
}

function scan() {
  const host = location.hostname;
  if (host.includes("tiktok.com")) {
    sendEmbedded("tiktok", extractTikTokEmbedded());
  } else if (host.includes("instagram.com")) {
    sendEmbedded("instagram", extractInstagramEmbedded());
  }
  // X embedded data travels via GraphQL responses; network capture covers it.
}

// run once at document_start + on SPA navigations (TikTok/IG are SPAs)
scan();
let lastUrl = location.href;
setInterval(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href;
    setTimeout(scan, 1500);   // let embedded JSON land
  }
}, 1000);