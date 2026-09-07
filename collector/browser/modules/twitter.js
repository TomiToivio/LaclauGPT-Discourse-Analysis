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

function extractTweets(obj, acc) {
  // walk any payload shape; tweet_results are the leaf carriers
  if (Array.isArray(obj)) { for (const v of obj) extractTweets(v, acc); return; }
  if (!obj || typeof obj !== "object") return;
  if (obj.tweet_results?.result) {
    acc.push(obj.tweet_results.result);
  }
  for (const k of Object.keys(obj)) extractTweets(obj[k], acc);
}

function oneRecord(r, via) {
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

export async function parse(response, source_platform_url, source_url) {
  const out = [];
  const seen = new Set();
  const add = (rec) => {
    if (!rec.post_id || seen.has(rec.post_id)) return;
    seen.add(rec.post_id);
    out.push(rec);
  };

  const dig = (obj, via) => {
    const acc = [];
    extractTweets(obj, acc);
    for (const r of acc) {
      const rec = oneRecord(r, via);
      // quoted tweets live nested; keep the outer one, note the quote
      add(rec);
      if (r.quoted_status_result?.result) {
        const q = oneRecord(r.quoted_status_result.result, via + "-quoted");
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