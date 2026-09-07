/**
 * LaclauGPT Instagram parser.
 *
 * The structure deliberately follows the original LaclauGPT scraper style:
 * identify the request, route it to a small parser, normalise one platform
 * object at a time, and emit LaclauGPT records. Instagram has changed its web
 * payloads repeatedly, so this module accepts several current GraphQL/API
 * shapes without copying another collector's parser architecture.
 *
 * Author: Tomi Toivio / LaclauGPT
 * License: CC0 1.0 Universal
 */

function asString(value) {
  return value === null || value === undefined ? "" : String(value);
}

function firstValue(...values) {
  return values.find(value => value !== null && value !== undefined && value !== "");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function toIsoTimestamp(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return null;
  try {
    return new Date(numeric * 1000).toISOString();
  } catch {
    return null;
  }
}

function resolveUrls(sourcePlatformUrl, sourceUrl) {
  const candidates = [sourcePlatformUrl, sourceUrl].filter(value => typeof value === "string" && value);
  const requestUrl = candidates.find(url => /instagram\.com\/(graphql|api|ajax)\b/i.test(url)) ?? sourcePlatformUrl ?? sourceUrl ?? "";
  const pageUrl = candidates.find(url => url !== requestUrl && /instagram\.com/i.test(url)) ?? sourceUrl ?? sourcePlatformUrl ?? "";
  return { requestUrl, pageUrl };
}

function profileHandle(pageUrl) {
  try {
    const path = new URL(pageUrl).pathname.split("/").filter(Boolean);
    if (!path.length) return null;
    const reserved = new Set([
      "p", "reel", "reels", "explore", "stories", "direct", "accounts",
      "popular", "about", "legal", "developer", "web",
    ]);
    if (reserved.has(path[0].toLowerCase())) return null;
    return path[0].toLowerCase();
  } catch {
    return null;
  }
}

function captionText(item) {
  const caption = item?.caption;
  if (typeof caption === "string") return caption;
  if (caption && typeof caption.text === "string") return caption.text;
  if (Array.isArray(caption) && typeof caption[0]?.text === "string") return caption[0].text;

  const edgeCaption = item?.edge_media_to_caption?.edges?.[0]?.node?.text;
  if (typeof edgeCaption === "string") return edgeCaption;
  return "";
}

function imageCandidates(item) {
  const urls = [];
  if (item?.display_url) urls.push(item.display_url);
  if (item?.display_src) urls.push(item.display_src);
  for (const candidate of item?.image_versions2?.candidates ?? []) {
    if (candidate?.url) urls.push(candidate.url);
  }
  return urls;
}

function videoCandidates(item) {
  const urls = [];
  if (item?.video_url) urls.push(item.video_url);
  for (const version of item?.video_versions ?? []) {
    if (version?.url) urls.push(version.url);
  }
  return urls;
}

function collectMedia(item) {
  const urls = [...videoCandidates(item), ...imageCandidates(item)];
  const children = item?.carousel_media ?? item?.edge_sidecar_to_children?.edges?.map(edge => edge?.node) ?? [];
  for (const child of children) {
    if (!child) continue;
    urls.push(...videoCandidates(child));
    urls.push(...imageCandidates(child));
  }
  return unique(urls);
}

function mediaType(item) {
  if (item?.media_type === 8 || item?.carousel_media || item?.edge_sidecar_to_children) return "carousel";
  if (item?.media_type === 2 || item?.is_video || /VideoMedia/i.test(item?.__typename ?? "")) return "video";
  return "image";
}

function parseInstagramItem(item, via, pageUrl) {
  if (!item || typeof item !== "object") return null;

  const user = item.user ?? item.owner ?? {};
  const shortcode = asString(firstValue(item.code, item.shortcode));
  const nativeId = asString(firstValue(item.pk, item.id, shortcode));
  if (!nativeId) return null;

  const username = firstValue(user.username, item.owner_username);
  const caption = captionText(item);
  const permalink = shortcode
    ? `https://www.instagram.com/${mediaType(item) === "video" ? "reel" : "p"}/${shortcode}/`
    : firstValue(item.permalink, item.link);

  return {
    post_id: nativeId,
    author: username ?? null,
    author_display: firstValue(user.full_name, user.name, username) ?? null,
    timestamp: toIsoTimestamp(firstValue(item.taken_at, item.taken_at_timestamp, item.created_time)),
    url: permalink ?? null,
    text: caption,
    hashtags: unique(caption.match(/#[\p{L}\p{N}_]+/gu) ?? []),
    engagement: {
      likes: firstValue(item.like_count, item.edge_media_preview_like?.count, item.edge_liked_by?.count),
      comments: firstValue(item.comment_count, item.edge_media_to_comment?.count, item.edge_media_to_parent_comment?.count),
      views: firstValue(item.view_count, item.play_count, item.video_view_count),
      reshares: firstValue(item.reshare_count, item.repost_count),
    },
    media_urls: collectMedia(item),
    media_type: mediaType(item),
    instagram: {
      shortcode: shortcode || null,
      native_id: nativeId,
      product_type: item.product_type ?? null,
      user_id: asString(firstValue(user.pk, user.id)) || null,
      user_verified: user.is_verified ?? null,
      user_followers: firstValue(user.follower_count, user.edge_followed_by?.count),
      accessibility_caption: item.accessibility_caption ?? null,
      page_url: pageUrl || null,
    },
    via,
  };
}

function looksLikeMedia(item) {
  if (!item || typeof item !== "object" || Array.isArray(item)) return false;
  const hasIdentity = Boolean(firstValue(item.pk, item.id, item.code, item.shortcode));
  const hasMediaSignal = Boolean(
    item.media_type || item.code || item.shortcode || item.image_versions2 ||
    item.video_versions || item.display_url || item.edge_media_to_caption ||
    /Polaris(?:Post|VideoMedia|ImageMedia)/i.test(item.__typename ?? "")
  );
  return hasIdentity && hasMediaSignal;
}

function collectInstagramItems(root) {
  const items = [];
  const seenObjects = new Set();

  function walk(node) {
    if (!node || typeof node !== "object") return;
    if (seenObjects.has(node)) return;
    seenObjects.add(node);

    if (Array.isArray(node)) {
      for (const child of node) walk(child);
      return;
    }

    if (looksLikeMedia(node)) {
      items.push(node);
      // Carousel children are media assets belonging to this post, not posts.
      return;
    }

    const preferredKeys = [
      "data", "items", "medias", "feed_items", "fill_items", "edges",
      "repost_grid_items", "two_by_two_item", "node", "media",
      "xdt_api__v1__feed__user_timeline_graphql_connection",
      "xdt_api__v1__feed__timeline__connection",
    ];

    let followedPreferredKey = false;
    for (const key of preferredKeys) {
      if (node[key] !== undefined) {
        followedPreferredKey = true;
        walk(node[key]);
      }
    }

    // GraphQL envelopes often introduce generated wrapper names. Only if none
    // of the known containers were present, descend one level through objects.
    if (!followedPreferredKey) {
      for (const [key, value] of Object.entries(node)) {
        if (["user", "owner", "caption", "audio", "music_metadata"].includes(key)) continue;
        if (value && typeof value === "object") walk(value);
      }
    }
  }

  walk(root);
  return items;
}

function dataGrabber(data, requestUrl, pageUrl) {
  if (!data || typeof data !== "object") return [];

  // Avoid obvious telemetry/background payloads. The old LaclauGPT scraper
  // routed only known content endpoints; this is the equivalent guard here.
  if (/logging_client_events|lightspeed_web_request_for_igd|injected_story_units/i.test(requestUrl)) {
    return [];
  }

  const visitedHandle = profileHandle(pageUrl);
  const records = [];
  for (const item of collectInstagramItems(data)) {
    const record = parseInstagramItem(item, /graphql/i.test(requestUrl) ? "graphql" : "api", pageUrl);
    if (!record) continue;

    // LaclauGPT contamination guard: when explicitly collecting a profile,
    // ignore preloaded/suggested posts from other accounts.
    if (visitedHandle && record.author && record.author.toLowerCase() !== visitedHandle) {
      continue;
    }
    records.push(record);
  }
  return records;
}

function parseEmbeddedHtml(html, pageUrl) {
  const records = [];
  const scripts = html.matchAll(/<script[^>]*type=["']application\/json["'][^>]*>([\s\S]*?)<\/script>/gi);
  for (const match of scripts) {
    try {
      records.push(...dataGrabber(JSON.parse(match[1]), "embedded-html", pageUrl));
    } catch {
      // Ignore unrelated or malformed application/json blocks.
    }
  }
  return records;
}

function deduplicate(records) {
  const byId = new Map();
  for (const record of records) {
    if (!record?.post_id) continue;
    const previous = byId.get(record.post_id);
    if (!previous || (record.media_urls?.length ?? 0) > (previous.media_urls?.length ?? 0)) {
      byId.set(record.post_id, record);
    }
  }
  return [...byId.values()];
}

export async function parse(response, sourcePlatformUrl, sourceUrl) {
  const { requestUrl, pageUrl } = resolveUrls(sourcePlatformUrl, sourceUrl);
  const records = [];

  if (response && typeof response === "object") {
    return deduplicate(dataGrabber(response, requestUrl, pageUrl));
  }
  if (typeof response !== "string" || !response.trim()) return [];

  let body = response.trim();
  if (body.startsWith("for (;;);")) body = body.slice("for (;;);".length);

  try {
    records.push(...dataGrabber(JSON.parse(body), requestUrl, pageUrl));
  } catch {
    records.push(...parseEmbeddedHtml(body, pageUrl));
  }

  return deduplicate(records);
}
