/**
 * TikTok parser — LaclauGPT Social Media Collector.
 *
 * Knowledge adapted from Zeeschuimer's modules/tiktok.js (DMI, MIT):
 * endpoint shapes (item_list API, webapp.updated-items, video-detail),
 * the SIGI_STATE / __UNIVERSAL_DATA_FOR_REHYDRATION__ embedded blocks,
 * itemStruct field paths. Re-implemented for LaclauGPT's record shape;
 * no verbatim upstream code. License respected: our file MIT, upstream MIT.
 */
export async function parse(response, source_platform_url, source_url) {
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
        plays: stats(item).play_count ?? null,
        likes: stats(item).digg_count ?? null,
        comments: stats(item).comment_count ?? null,
        shares: stats(item).share_count ?? null,
        collects: stats(item).collect_count ?? null,
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