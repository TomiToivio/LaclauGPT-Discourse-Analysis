/**
 * LaclauGPT TikTok parser.
 *
 * This module follows the architecture of the original 2024
 * LaclauGPT-TikTok-Scraper: explicit request routing, small platform-specific
 * parsers, and a LaclauGPT-owned record shape. Modern TikTok response shapes
 * are handled here as compatibility cases rather than by mirroring another
 * collector's module structure.
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

function toIsoTimestamp(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return null;
  try {
    return new Date(numeric * 1000).toISOString();
  } catch {
    return null;
  }
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function resolveUrls(sourcePlatformUrl, sourceUrl) {
  const candidates = [sourcePlatformUrl, sourceUrl].filter(value => typeof value === "string" && value);
  const requestUrl = candidates.find(url => /tiktok\.com\/(api|aweme)\//i.test(url)) ?? sourcePlatformUrl ?? sourceUrl ?? "";
  const pageUrl = candidates.find(url => url !== requestUrl && /tiktok\.com/i.test(url)) ?? sourceUrl ?? sourcePlatformUrl ?? "";
  return { requestUrl, pageUrl };
}

function normalizeStats(item) {
  const stats = item?.stats ?? item?.statsV2 ?? {};
  return {
    plays: firstValue(stats.playCount, stats.play_count),
    likes: firstValue(stats.diggCount, stats.digg_count),
    comments: firstValue(stats.commentCount, stats.comment_count),
    shares: firstValue(stats.shareCount, stats.share_count),
    collects: firstValue(stats.collectCount, stats.collect_count),
  };
}

function normalizeAuthor(item) {
  const author = item?.author && typeof item.author === "object" ? item.author : {};
  const authorStats = item?.authorStats ?? {};
  return {
    id: firstValue(author.id, author.uid),
    username: firstValue(author.uniqueId, author.unique_id, typeof item?.author === "string" ? item.author : null),
    display_name: firstValue(author.nickname, item?.nickname),
    avatar: firstValue(author.avatarLarger, author.avatarMedium, author.avatarThumb),
    signature: author.signature ?? null,
    verified: author.verified ?? null,
    followers: firstValue(authorStats.followerCount, authorStats.follower_count),
    following: firstValue(authorStats.followingCount, authorStats.following_count),
    videos: firstValue(authorStats.videoCount, authorStats.video_count),
    likes: firstValue(authorStats.heartCount, authorStats.heart, authorStats.diggCount),
  };
}

function normalizeMedia(item) {
  const video = item?.video ?? {};
  const playAddress = firstValue(video.downloadAddr, video.download_addr, video.playAddr, video.play_addr);
  const cover = firstValue(video.cover, video.dynamicCover, video.originCover);
  return {
    video_url: playAddress ?? null,
    cover_url: cover ?? null,
    duration: firstValue(video.duration, item?.videoDuration),
    width: video.width ?? null,
    height: video.height ?? null,
    ratio: video.ratio ?? null,
    media_urls: unique([
      playAddress,
      video.playAddr,
      video.play_addr,
      video.downloadAddr,
      video.download_addr,
      cover,
    ]),
  };
}

function normalizeMusic(item) {
  const music = item?.music ?? {};
  if (!Object.keys(music).length) return null;
  return {
    id: music.id ?? null,
    title: music.title ?? null,
    author: firstValue(music.authorName, music.author),
    original: music.original ?? null,
    play_url: firstValue(music.playUrl, music.play_url),
    cover_url: firstValue(music.coverLarge, music.coverMedium, music.coverThumb),
    duration: music.duration ?? null,
  };
}

function parseVideoItem(item, via, pageUrl = "") {
  if (!item || typeof item !== "object" || item.liveRoomInfo) return null;

  const id = asString(firstValue(item.id, item.aweme_id));
  if (!id) return null;

  const author = normalizeAuthor(item);
  const media = normalizeMedia(item);
  const description = firstValue(item.desc, item.description, "") ?? "";
  const hashtags = (item.textExtra ?? item.text_extra ?? [])
    .filter(tag => tag && firstValue(tag.hashtagName, tag.hashtag_name))
    .map(tag => `#${firstValue(tag.hashtagName, tag.hashtag_name)}`);

  const fallbackUrl = author.username
    ? `https://www.tiktok.com/@${author.username}/video/${id}`
    : `https://www.tiktok.com/video/${id}`;

  return {
    post_id: id,
    author: author.username ?? null,
    author_display: author.display_name ?? null,
    timestamp: toIsoTimestamp(firstValue(item.createTime, item.create_time)),
    url: firstValue(item.shareUrl, item.share_url, fallbackUrl),
    text: description,
    hashtags: unique(hashtags),
    engagement: normalizeStats(item),
    media_urls: media.media_urls,
    music: normalizeMusic(item),
    tiktok: {
      author,
      media,
      location_created: firstValue(item.locationCreated, item.location_created),
      effects: (item.effectStickers ?? []).map(effect => effect?.name).filter(Boolean),
      challenges: (item.challenges ?? []).map(challenge => challenge?.title).filter(Boolean),
      duet_from_id: item.duetInfo?.duetFromId ?? null,
      is_ad: item.isAd ?? null,
      page_url: pageUrl || null,
    },
    via,
  };
}

function parseVideoList(data, via, pageUrl) {
  const list = data?.itemList ?? data?.item_list ?? [];
  if (!Array.isArray(list)) return [];
  return list.map(item => parseVideoItem(item, via, pageUrl)).filter(Boolean);
}

function parseSearchResults(data, pageUrl) {
  const results = Array.isArray(data?.data) ? data.data : [];
  const posts = [];
  for (const result of results) {
    const item = result?.item ?? result?.itemStruct ?? null;
    if (!item) continue;
    const record = parseVideoItem(item, "search", pageUrl);
    if (record) posts.push(record);
  }
  return posts;
}

function parseUserPlaylist(data, pageUrl) {
  const list = data?.itemList ?? data?.item_list ?? [];
  if (!Array.isArray(list)) return [];
  return list
    .map(entry => entry?.item ?? entry)
    .map(item => parseVideoItem(item, "playlist", pageUrl))
    .filter(Boolean);
}

function parseItemModule(data, pageUrl) {
  const module = data?.ItemModule;
  if (!module || typeof module !== "object") return [];
  return Object.values(module)
    .map(item => parseVideoItem(item, "embedded-SIGI", pageUrl))
    .filter(Boolean);
}

function parseUniversalData(data, pageUrl) {
  const scope = data?.__DEFAULT_SCOPE__ ?? data?.__DEFAULT_SCOPE;
  if (!scope || typeof scope !== "object") return [];

  const posts = [];
  const updated = scope["webapp.updated-items"];
  if (Array.isArray(updated)) {
    for (const entry of updated) {
      const record = parseVideoItem(entry?.itemStruct ?? entry, "embedded-UDR", pageUrl);
      if (record) posts.push(record);
    }
  }

  const detail = scope["webapp.video-detail"]?.itemInfo?.itemStruct;
  if (detail) {
    const record = parseVideoItem(detail, "video-detail", pageUrl);
    if (record) posts.push(record);
  }
  return posts;
}

function dataGrabber(data, requestUrl, pageUrl) {
  if (!data || typeof data !== "object") return [];

  if (data.ItemModule) return parseItemModule(data, pageUrl);
  if (data.__DEFAULT_SCOPE__) return parseUniversalData(data, pageUrl);

  if (/search\/general\/full|search\/item|search\/video/i.test(requestUrl)) {
    return parseSearchResults(data, pageUrl);
  }
  if (/user\/playlist/i.test(requestUrl)) {
    return parseUserPlaylist(data, pageUrl);
  }
  if (/post\/item_list|challenge\/item_list|item_list/i.test(requestUrl)) {
    return parseVideoList(data, "item-list", pageUrl);
  }

  // TikTok changes endpoint names frequently. If the response itself contains
  // a recognisable post list, accept it even when the route is new.
  if (Array.isArray(data.itemList) || Array.isArray(data.item_list)) {
    return parseVideoList(data, "item-list-fallback", pageUrl);
  }
  if (Array.isArray(data.data)) {
    return parseSearchResults(data, pageUrl);
  }
  return [];
}

function parseEmbeddedHtml(html, pageUrl) {
  const posts = [];

  const sigi = html.match(/<script[^>]+id=["']SIGI_STATE["'][^>]*>([\s\S]*?)<\/script>/i);
  if (sigi?.[1]) {
    try {
      posts.push(...parseItemModule(JSON.parse(sigi[1]), pageUrl));
    } catch {
      // Ignore malformed or incomplete page state.
    }
  }

  const universal = html.match(/<script[^>]+id=["']__UNIVERSAL_DATA_FOR_REHYDRATION__["'][^>]*>([\s\S]*?)<\/script>/i);
  if (universal?.[1]) {
    try {
      posts.push(...parseUniversalData(JSON.parse(universal[1]), pageUrl));
    } catch {
      // Ignore malformed or incomplete page state.
    }
  }
  return posts;
}

function deduplicate(records) {
  const seen = new Set();
  return records.filter(record => {
    if (!record?.post_id || seen.has(record.post_id)) return false;
    seen.add(record.post_id);
    return true;
  });
}

export async function parse(response, sourcePlatformUrl, sourceUrl) {
  const { requestUrl, pageUrl } = resolveUrls(sourcePlatformUrl, sourceUrl);
  const records = [];

  if (response && typeof response === "object") {
    records.push(...dataGrabber(response, requestUrl, pageUrl));
    records.push(...parseUniversalData(response, pageUrl));
    return deduplicate(records);
  }

  if (typeof response !== "string" || !response.trim()) return [];

  try {
    const data = JSON.parse(response);
    records.push(...dataGrabber(data, requestUrl, pageUrl));
  } catch {
    records.push(...parseEmbeddedHtml(response, pageUrl));
  }

  return deduplicate(records);
}
