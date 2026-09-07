/* BUNDLED background — LaclauGPT collector (issue #20).
   MV2 non-module background: parser modules inlined as plain functions.
   Upstream attribution: Zeeschuimer (DMI, MIT) + LaclauGPT-TikTok-Scraper (CC0). */

/**
 * TikTok parser — LaclauGPT Social Media Collector.
 *
 * Knowledge adapted from Zeeschuimer's modules/tiktok.js (DMI, MIT):
 * endpoint shapes (item_list API, webapp.updated-items, video-detail),
 * the SIGI_STATE / __UNIVERSAL_DATA_FOR_REHYDRATION__ embedded blocks,
 * itemStruct field paths. Re-implemented for LaclauGPT's record shape;
 * no verbatim upstream code. License respected: our file MIT, upstream MIT.
 */
async function parse_tiktok(response, source_platform_url, source_url) {
  const out = [];
  const add = (item, via) => {
    if (!item || !item.id) return;
    const author = item.author ?? {};
    const music = item.music ?? {};
    const video = item.video ?? {};
    out.push({
      post_id: String(item.id),
      author: author.unique_id ?? author.uniqueId ?? author.secUid ?? null,
      author_display: author.nickname ?? null,
      timestamp: item.create_time
        ? new Date(Number(item.create_time) * 1000).toISOString()
        : null,
      url: item.share_url ?? `https://www.tiktok.com/@${author.unique_id ?? ""}/video/${item.id}`,
      text: item.desc ?? "",
      hashtags: [...(item.textExtra ?? [])].filter(t => t?.hashtagName).map(t => "#" + t.hashtagName),
      engagement: {
        plays: tt_stats(item).play_count ?? null,
        likes: tt_stats(item).digg_count ?? null,
        comments: tt_stats(item).comment_count ?? null,
        shares: tt_stats(item).share_count ?? null,
        collects: tt_stats(item).collect_count ?? null,
      },
      media_urls: [video.play_addr, video.download_addr, video.cover].filter(Boolean),
      music: music.title ? { title: music.title, author: music.author } : null,
      via,                                    // "item_list" | "embedded" | "preload"
    });
  };
  const stats = (i) => i.stats ?? i.statsV2 ?? {};

  // 1) Zeeschuimer-style: JSON API responses (item_list, preload)
  if (typeof response === "string" && response.trim().startsWith("{")) {
    try {
      const data = JSON.parse(response);
      const lists = [];
      if (data?.itemList) lists.push(...data.itemList);
      if (data?.item_list) lists.push(...data.item_list);
      if (data?.itemListData) lists.push(...data.itemListData.map(x => x.item ?? x));
      if (data?.statusCode !== undefined && data?.itemList) lists.push(...data.itemList);
      for (const it of lists) add(it, "item_list");
    } catch (e) { /* not JSON */ }
  }

  // 2) embedded page state (content script sends the parsed JSON through
  //    background; here we also accept raw HTML for robustness)
  if (typeof response === "string" && response.includes("SIGI_STATE")) {
    try {
      const m = response.match(/<script id="SIGI_STATE"[^>]*>([\s\S]*?)<\/script>/);
      if (m) {
        const state = JSON.parse(m[1]);
        const items = state?.ItemModule ? Object.values(state.itemList ?? {}) : [];
        for (const it of items) add(it, "embedded-SIGI");
      }
    } catch (e) {}
    try {
      const m2 = response.match(/<script[^>]+__UNIVERSAL_DATA_FOR_REHYDRATION__[^>]*>([\s\S]*?)<\/script>/);
      if (m2) {
        const scope = JSON.parse(m2[1])?.__DEFAULT_SCOPE__;
        const upd = scope?.["webapp.updated-items"];
        if (Array.isArray(upd)) for (const it of upd) add(it.itemStruct ?? it, "embedded-UDR");
        const detail = scope?.["webapp.video-detail"]?.itemInfo?.itemStruct;
        if (detail) add(detail, "embedded-video-detail");
      }
    } catch (e) {}
  }

  // 3) object form (embedded payloads arrive pre-parsed from content.js)
  if (typeof response === "object") {
    const scope = response?.__DEFAULT_SCOPE__;
    const upd = scope?.["webapp.updated-items"];
    if (Array.isArray(upd)) for (const it of upd) add(it.itemStruct ?? it, "embedded-UD-object");
  }

  return out;
}

/**
 * Instagram parser — LaclauGPT Social Media Collector.
 *
 * Knowledge adapted from Zeeschuimer's modules/instagram.js (DMI, MIT):
 * xdt_api__v1__feed__user_timeline_graphql_connection /
 * xdt_api__v1__feed__timeline__connection shapes, media item structures
 * (carousel_media, video_versions, display_url), taken_at timestamps.
 * IMPORTANT (Zeeschuimer rule, kept): only posts from the visited account
 * pass the filter — background/preloaded material is dropped so the
 * researcher's own feed never leaks into the corpus.
 * Re-implemented for LaclauGPT's record shape. MIT both ways.
 */

function tt_walkCandidates(node) {
  // Yields every plausible media item in a GraphQL connection payload
  const items = [];
  const conn = node?.xdt_api__v1__feed__user_timeline_graphql_connection ??
               node?.xdt_api__v1__feed__timeline__connection;
  const edges = conn?.edges ?? [];
  for (const e of edges) {
    const n = e?.node;
    if (!n) continue;
    if (n.__typename === "XIGPolarisPost" ||
        n.__typename === "XIGPolarisVideoMedia" ||
        n.code || n.media_type) {
      items.push(n);
    }
    // carousels hold children
    for (const child of n.carousel_media ?? []) items.push(child);
  }
  return items;
}

function tt_oneRecord(n, via) {
  const user = n.user ?? {};
  const mediaType = ({1: "image", 2: "video", 8: "carousel"})[n.media_type] ??
                    (n.__typename === "XIGPolarisVideoMedia" ? "video" : "image");
  const mediaUrls = [];
  for (const vi of n.video_versions ?? []) mediaUrls.push(vi.url);
  for (const im of n.image_versions2?.candidates ?? []) mediaUrls.push(im.url);
  // caption is a list of objects
  const caption = Array.isArray(n.caption) && n.caption.length
    ? n.caption[0].text : (typeof n.caption === "string" ? n.caption : "");

  return {
    post_id: String(n.code ?? n.pk ?? n.id ?? ""),       // IG canonical = shortcode
    author: user.username ?? null,
    author_display: user.full_name ?? user.username ?? null,
    timestamp: n.taken_at ? new Date(Number(n.taken_at) * 1000).toISOString() : null,
    url: n.code ? `https://www.instagram.com/p/${n.code}/` : null,
    text: caption,
    hashtags: (caption.match(/#[\p{L}0-9_]+/gu) ?? []).slice(0, 30),
    engagement: {
      likes: n.like_count ?? null,
      comments: n.comment_count ?? null,
      views: n.view_count ?? n.play_count ?? null,
    },
    media_urls: mediaUrls.filter(Boolean).slice(0, 12),
    media_type: mediaType,
    via,
  };
}

async function parse_instagram(response, source_platform_url, source_url) {
  const out = [];
  const seen = new Set();
  const add = (rec) => {
    if (!rec.post_id || seen.has(rec.post_id)) return;
    seen.add(rec.post_id);
    out.push(rec);
  };

  const handleFromUrl = (() => {
    try {
      const u = new URL(source_platform_url);
      const m = u.pathname.match(/^\/([^/]+)\/?/);
      return m && !["p", "reel", "explore", "accounts"].includes(m[1]) ? m[1].toLowerCase() : null;
    } catch { return null; }
  })();

  const dig = (obj, via) => {
    if (!obj || typeof obj !== "object") return;
    const conn = obj.xdt_api__v1__feed__user_timeline_graphql_connection ??
                 obj.xdt_api__v1__feed__timeline__connection;
    if (conn) {
      for (const n of ig_walkCandidates(obj)) {
        const rec = ig_oneRecord(n, via);
        // Zeeschuimer ownership filter: only visited-account posts
        if (handleFromUrl && rec.author &&
            rec.author.toLowerCase() !== handleFromUrl) continue;
        add(rec);
      }
      return;
    }
    // single post / reel pages
    if (obj.shortcode || obj.pk) add(ig_oneRecord(obj, via));
    for (const k of Object.keys(obj)) dig(obj[k], via);
  };

  if (typeof response === "string") {
    // GraphQL responses arrive as JSON; embedded scripts as HTML-wrapped JSON
    try { dig(JSON.parse(response), "graphql"); }
    catch (e) {
      try { dig(JSON.parse(response.match(/<script[^>]*type="application\/json"[^>]*>([\s\S]*?)<\/script>/)?.[1] ?? "{}"), "embedded"); }
      catch (e2) {}
    }
  } else if (typeof response === "object") {
    dig(response, "embedded-object");
  }
  return out;
}

/**
 * X/Twitter parser — LaclauGPT Social Media Collector.
 *
 * Knowledge adapted from Zeeschuimer's modules/twitter.js (DMI, MIT):
 * GraphQL timeline shape (tweet_results → result → legacy), rest_id as the
 * post id, full_text + entity media, operation-name based capture (never
 * hard-coded GraphQL query ids — they rotate).
 * CRITICAL RULE (kept from Zeeschuimer + issue #20): post ids are STRINGs,
 * never parsed as integers — X ids exceed JS safe-integer range.
 * Re-implemented for LaclauGPT's record shape. MIT both ways.
 */

function ig_extractTweets(obj, acc) {
  // walk any payload shape; tweet_results are the leaf carriers
  if (Array.isArray(obj)) { for (const v of obj) ig_extractTweets(v, acc); return; }
  if (!obj || typeof obj !== "object") return;
  if (obj.tweet_results?.result) {
    acc.push(obj.tweet_results.result);
  }
  for (const k of Object.keys(obj)) ig_extractTweets(obj[k], acc);
}

function ig_oneRecord(r, via) {
  const legacy = r.legacy ?? {};
  const user = r.core?.user_results?.result?.legacy ??
               r.core?.user?.legacy ?? {};
  const id = String(r.rest_id ?? legacy.id_str ?? "");
  const text = legacy.full_text ?? legacy.text ?? "";
  const urls = [];
  let mediaUrls = [];
  for (const m of legacy.extended_entities?.media ?? legacy.entities?.media ?? []) {
    if (m.video_info?.variants) {
      mediaUrls.push(...m.video_info.variants
        .filter(v => v.content_type === "video/mp4")
        .map(v => v.url));
    }
    if (m.media_url_https) mediaUrls.push(m.media_url_https);
  }
  for (const u of legacy.entities?.urls ?? []) if (u.expanded_url) urls.push(u.url);
  return {
    post_id: id,                                    // STRING by construction
    author: user.screen_name ?? null,
    author_display: user.name ?? null,
    timestamp: legacy.created_at
      ? new Date(legacy.created_at).toISOString() : null,
    url: id && (user.screen_name || legacy.entities?.user_mentions?.[0])
      ? `https://x.com/${user.screen_name ?? legacy.in_reply_to_screen_name ?? "i"}/status/${id}`
      : (id ? `https://x.com/i/status/${id}` : null),
    text,
    parent_post_id: legacy.in_reply_to_status_id_str ?? null,
    relation: legacy.in_reply_to_status_id_str ? "reply" :
              (legacy.retweeted_status_result ? "repost" : null),
    hashtags: (legacy.entities?.hashtags ?? []).map(h => "#" + h.text),
    mentions: (legacy.entities?.user_mentions ?? []).map(m => "@" + m.screen_name),
    urls,
    engagement: {
      retweets: legacy.retweet_count ?? null,
      likes: legacy.favorite_count ?? null,
      replies: legacy.reply_count ?? null,
      quotes: legacy.quote_count ?? null,
      views: legacy.views?.count ? Number(legacy.views.count) : null,
      bookmarks: legacy.bookmark_count ?? null,
    },
    media_urls: mediaUrls.slice(0, 6),
    language: legacy.lang ?? null,
    via,
  };
}

async function parse_x(response, source_platform_url, source_url) {
  const out = [];
  const seen = new Set();
  const add = (rec) => {
    if (!rec.post_id || seen.has(rec.post_id)) return;
    seen.add(rec.post_id);
    out.push(rec);
  };

  const dig = (obj, via) => {
    const acc = [];
    tw_extractTweets(obj, acc);
    for (const r of acc) {
      const rec = tw_oneRecord(r, via);
      // quoted tweets live nested; keep the outer one, note the quote
      add(rec);
      if (r.quoted_status_result?.result) {
        const q = tw_oneRecord(r.quoted_status_result.result, via + "-quoted");
        if (q.post_id) { q.relation = "quote"; add(q); }
      }
    }
  };

  if (typeof response === "string") {
    try { dig(JSON.parse(response), "graphql"); } catch (e) {}
  } else if (typeof response === "object") {
    dig(response, "embedded-object");
  }
  return out;
}

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

const PARSERS = [
  { match: /tiktok\.com/i, name: "tiktok", fn: parse_tiktok },
  { match: /instagram\.com/i, name: "instagram", fn: parse_instagram },
  { match: /(twitter|x)\.com/i, name: "x", fn: parse_x },
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