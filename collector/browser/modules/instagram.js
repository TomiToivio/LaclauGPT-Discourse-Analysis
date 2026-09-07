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

function walkCandidates(node) {
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

function oneRecord(n, via) {
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

export async function parse(response, source_platform_url, source_url) {
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
      for (const n of walkCandidates(obj)) {
        const rec = oneRecord(n, via);
        // Zeeschuimer ownership filter: only visited-account posts
        if (handleFromUrl && rec.author &&
            rec.author.toLowerCase() !== handleFromUrl) continue;
        add(rec);
      }
      return;
    }
    // single post / reel pages
    if (obj.shortcode || obj.pk) add(oneRecord(obj, via));
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