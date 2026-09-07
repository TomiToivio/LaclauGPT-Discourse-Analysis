/**
 * LaclauGPT X/Twitter parser.
 *
 * This module uses the original LaclauGPT scraper pattern: route known API
 * responses explicitly, parse individual platform objects in small functions,
 * and emit a LaclauGPT-owned record format. Query IDs are intentionally not
 * part of the parser because X changes them frequently; stable operation names
 * and response structure are used instead.
 *
 * IMPORTANT: post IDs are always strings. X IDs exceed JavaScript's safe
 * integer range and must never be parsed with parseInt/Number.
 *
 * Author: Tomi Toivio / LaclauGPT
 * License: CC0 1.0 Universal
 */

const POST_OPERATIONS = [
  "adaptive.json",
  "HomeTimeline",
  "HomeLatestTimeline",
  "ListLatestTweetsTimeline",
  "SearchTimeline",
  "TweetDetail",
  "UserTweets",
  "UserTweetsAndReplies",
  "UserOriginalsTimeline",
  "UserRepliesTimeline",
  "UserRepostsTimeline",
  "UserPhotoTimeline",
  "UserVideoTimeline",
  "ExplorePage",
  "Likes",
];

function asString(value) {
  return value === null || value === undefined ? "" : String(value);
}

function firstValue(...values) {
  return values.find(value => value !== null && value !== undefined && value !== "");
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function resolveUrls(sourcePlatformUrl, sourceUrl) {
  const candidates = [sourcePlatformUrl, sourceUrl].filter(value => typeof value === "string" && value);
  const requestUrl = candidates.find(url => /\/graphql\/|adaptive\.json|\/i\/api\//i.test(url)) ?? sourcePlatformUrl ?? sourceUrl ?? "";
  const pageUrl = candidates.find(url => url !== requestUrl && /(?:x|twitter)\.com/i.test(url)) ?? sourceUrl ?? sourcePlatformUrl ?? "";
  return { requestUrl, pageUrl };
}

function endpointCarriesPosts(requestUrl) {
  if (!requestUrl) return true;
  if (!/(?:x|twitter)\.com/i.test(requestUrl)) return false;
  if (!/\/graphql\/|adaptive\.json|\/i\/api\//i.test(requestUrl)) return true;
  return POST_OPERATIONS.some(operation => requestUrl.includes(operation));
}

function unwrapTweet(result) {
  let current = result;
  for (let i = 0; i < 3; i += 1) {
    if (!current || typeof current !== "object") return null;
    if (current.__typename === "TweetUnavailable") return null;
    if (current.tweet && typeof current.tweet === "object") {
      current = current.tweet;
      continue;
    }
    break;
  }
  return current;
}

function userFromTweet(tweet) {
  const result = tweet?.core?.user_results?.result ?? tweet?.core?.user?.result ?? tweet?.user ?? {};
  const legacy = result?.legacy ?? result ?? {};
  return {
    id: asString(firstValue(result.rest_id, legacy.id_str)) || null,
    username: firstValue(legacy.screen_name, result.screen_name),
    display_name: firstValue(legacy.name, result.name),
    avatar: firstValue(legacy.profile_image_url_https, result.profile_image_url_https),
    banner: firstValue(legacy.profile_banner_url, result.profile_banner_url),
    description: firstValue(legacy.description, result.description),
    location: firstValue(legacy.location, result.location),
    followers: firstValue(legacy.followers_count, result.followers_count),
    following: firstValue(legacy.friends_count, result.friends_count),
    verified: firstValue(result.is_blue_verified, legacy.verified, result.verified),
  };
}

function tweetText(tweet) {
  return firstValue(
    tweet?.note_tweet?.note_tweet_results?.result?.text,
    tweet?.legacy?.full_text,
    tweet?.legacy?.text,
    tweet?.full_text,
    tweet?.text,
    "",
  ) ?? "";
}

function extractMedia(tweet) {
  const legacy = tweet?.legacy ?? tweet ?? {};
  const media = legacy.extended_entities?.media ?? legacy.entities?.media ?? [];
  const images = [];
  const videos = [];

  for (const item of media) {
    if (item?.media_url_https) images.push(item.media_url_https);
    for (const variant of item?.video_info?.variants ?? []) {
      if (variant?.content_type === "video/mp4" && variant?.url) videos.push(variant.url);
    }
  }
  return { images: unique(images), videos: unique(videos) };
}

function extractUrls(legacy) {
  const urls = [];
  for (const item of legacy?.entities?.urls ?? []) {
    const expanded = firstValue(item.expanded_url, item.unwound_url, item.url);
    if (expanded) urls.push(expanded);
  }
  return unique(urls);
}

function parseTweetItem(result, via, fallbackUser = null, pageUrl = "") {
  const tweet = unwrapTweet(result);
  if (!tweet) return null;

  const legacy = tweet.legacy ?? tweet;
  const id = asString(firstValue(tweet.rest_id, tweet.id, legacy.id_str));
  if (!id) return null;

  const user = fallbackUser ?? userFromTweet(tweet);
  const media = extractMedia(tweet);
  const replyTo = asString(legacy.in_reply_to_status_id_str) || null;
  const quotedId = asString(firstValue(
    legacy.quoted_status_id_str,
    tweet.quoted_status_result?.result?.rest_id,
    tweet.quoted_status_result?.result?.tweet?.rest_id,
  )) || null;
  const reposted = Boolean(legacy.retweeted_status_result || tweet.retweeted_status_result);

  let relation = null;
  if (replyTo) relation = "reply";
  else if (reposted) relation = "repost";
  else if (quotedId || legacy.is_quote_status) relation = "quote";

  const username = user?.username ?? legacy.in_reply_to_screen_name ?? null;
  const permalink = username
    ? `https://x.com/${username}/status/${id}`
    : `https://x.com/i/status/${id}`;

  const created = legacy.created_at ? new Date(legacy.created_at) : null;
  const timestamp = created && !Number.isNaN(created.getTime()) ? created.toISOString() : null;

  return {
    post_id: id,
    author: username,
    author_display: user?.display_name ?? username,
    timestamp,
    url: permalink,
    text: tweetText(tweet),
    parent_post_id: replyTo,
    quoted_post_id: quotedId,
    relation,
    hashtags: (legacy.entities?.hashtags ?? [])
      .map(tag => tag?.text ? `#${tag.text}` : null)
      .filter(Boolean),
    mentions: (legacy.entities?.user_mentions ?? [])
      .map(mention => mention?.screen_name ? `@${mention.screen_name}` : null)
      .filter(Boolean),
    urls: extractUrls(legacy),
    engagement: {
      reposts: firstValue(legacy.retweet_count, legacy.repost_count),
      likes: legacy.favorite_count ?? null,
      replies: legacy.reply_count ?? null,
      quotes: legacy.quote_count ?? null,
      bookmarks: legacy.bookmark_count ?? null,
      views: firstValue(tweet.views?.count, legacy.views?.count),
    },
    media_urls: unique([...media.images, ...media.videos]),
    language: legacy.lang ?? null,
    x: {
      conversation_id: asString(firstValue(legacy.conversation_id_str, tweet.conversation_id_str)) || null,
      user,
      image_urls: media.images,
      video_urls: media.videos,
      possibly_sensitive: legacy.possibly_sensitive ?? null,
      promoted: tweet.promoted ?? false,
      page_url: pageUrl || null,
    },
    via,
  };
}

function parseTimelineEntry(entry, posts) {
  if (!entry || typeof entry !== "object") return;
  const content = entry.content ?? entry.item ?? entry;
  const itemContent = content.itemContent ?? content.item?.itemContent;

  if (itemContent?.tweet_results?.result) {
    posts.push({ result: itemContent.tweet_results.result, via: "timeline" });
  }

  const moduleItems = content.items ?? [];
  for (const moduleItem of moduleItems) {
    const nested = moduleItem?.item?.itemContent ?? moduleItem?.itemContent;
    if (nested?.tweet_results?.result) {
      posts.push({ result: nested.tweet_results.result, via: "conversation" });
    }
  }
}

function parseTimelineInstructions(root) {
  const posts = [];
  const visited = new Set();

  function walk(node) {
    if (!node || typeof node !== "object" || visited.has(node)) return;
    visited.add(node);

    if (Array.isArray(node)) {
      for (const child of node) walk(child);
      return;
    }

    if (node.type === "TimelineAddEntries" && Array.isArray(node.entries)) {
      for (const entry of node.entries) parseTimelineEntry(entry, posts);
      return;
    }
    if (node.type === "TimelinePinEntry" && node.entry) {
      parseTimelineEntry(node.entry, posts);
      return;
    }

    // Some GraphQL envelopes omit the instruction type but still expose the
    // timeline entries directly.
    if (Array.isArray(node.entries) && node.entries.some(entry => entry?.entryId || entry?.content)) {
      for (const entry of node.entries) parseTimelineEntry(entry, posts);
    }

    for (const [key, value] of Object.entries(node)) {
      if (["legacy", "entities", "extended_entities", "user_results"].includes(key)) continue;
      if (value && typeof value === "object") walk(value);
    }
  }

  walk(root);
  return posts;
}

function parseDirectTweetResults(root) {
  const posts = [];
  const visited = new Set();

  function walk(node) {
    if (!node || typeof node !== "object" || visited.has(node)) return;
    visited.add(node);
    if (Array.isArray(node)) {
      for (const child of node) walk(child);
      return;
    }

    if (node.tweet_results?.result) {
      posts.push({ result: node.tweet_results.result, via: "graphql-result" });
      return;
    }
    for (const value of Object.values(node)) {
      if (value && typeof value === "object") walk(value);
    }
  }

  walk(root);
  return posts;
}

function parseAdaptive(data, pageUrl) {
  const tweets = data?.globalObjects?.tweets ?? {};
  const users = data?.globalObjects?.users ?? {};
  const records = [];

  for (const [id, legacy] of Object.entries(tweets)) {
    const userLegacy = users?.[legacy?.user_id_str] ?? {};
    const fallbackUser = {
      id: asString(firstValue(userLegacy.id_str, legacy?.user_id_str)) || null,
      username: userLegacy.screen_name ?? null,
      display_name: userLegacy.name ?? null,
      avatar: userLegacy.profile_image_url_https ?? null,
      banner: userLegacy.profile_banner_url ?? null,
      description: userLegacy.description ?? null,
      location: userLegacy.location ?? null,
      followers: userLegacy.followers_count ?? null,
      following: userLegacy.friends_count ?? null,
      verified: userLegacy.verified ?? null,
    };
    const record = parseTweetItem({ id: asString(id), legacy }, "adaptive", fallbackUser, pageUrl);
    if (record) records.push(record);
  }
  return records;
}

function dataGrabber(data, requestUrl, pageUrl) {
  if (!data || typeof data !== "object" || !endpointCarriesPosts(requestUrl)) return [];

  if (data.globalObjects?.tweets) {
    return parseAdaptive(data, pageUrl);
  }

  const candidates = [
    ...parseTimelineInstructions(data),
    ...parseDirectTweetResults(data),
  ];

  const records = [];
  for (const candidate of candidates) {
    const record = parseTweetItem(candidate.result, candidate.via, null, pageUrl);
    if (record) records.push(record);

    const tweet = unwrapTweet(candidate.result);
    const quote = tweet?.quoted_status_result?.result;
    if (quote) {
      const quotedRecord = parseTweetItem(quote, "quoted", null, pageUrl);
      if (quotedRecord) {
        quotedRecord.relation = "quoted-source";
        records.push(quotedRecord);
      }
    }
  }
  return records;
}

function deduplicate(records) {
  const byId = new Map();
  for (const record of records) {
    if (!record?.post_id) continue;
    const previous = byId.get(record.post_id);
    if (!previous || (record.text?.length ?? 0) > (previous.text?.length ?? 0)) {
      byId.set(record.post_id, record);
    }
  }
  return [...byId.values()];
}

export async function parse(response, sourcePlatformUrl, sourceUrl) {
  const { requestUrl, pageUrl } = resolveUrls(sourcePlatformUrl, sourceUrl);
  if (!endpointCarriesPosts(requestUrl)) return [];

  let data = response;
  if (typeof response === "string") {
    if (!response.trim()) return [];
    try {
      data = JSON.parse(response);
    } catch {
      return [];
    }
  }
  if (!data || typeof data !== "object") return [];

  return deduplicate(dataGrabber(data, requestUrl, pageUrl));
}
