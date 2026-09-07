# -*- coding: utf-8 -*-
"""Zeeschuimer autoscraper — Brazil 2026 election study.

Architecture (decided): Zeeschuimer-style API interception in a
persistent logged-in browser session, driven headlessly. Each account
page is scrolled; platform API responses are captured from the network
layer (the same data Zeeschuimer's Firefox extension grabs), saved as
NDJSON per account/platform/day. z4sync then pulls finished datasets
into the LaclauGPT pipeline.

Why interception instead of DOM scraping: X and Instagram serve
rendered HTML that is hostile to parsing and rate-limits aggressively;
their public JSON endpoints (which Zeeschuimer taps) are stable and
carry full metadata (author, timestamps, engagement).

Usage:
    python autoscraper.py --accounts accounts.yaml --out /path/data \
        [--platforms tiktok,x,instagram] [--scrolls 12] [--headed]

Login state lives in a persistent Chromium profile (first run: open
with --headed, log in to X/Instagram/TikTok manually once, keep the
cookies; afterwards runs are headless).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

AB = str(Path.home() / ".hermes/hermes-agent/node_modules/.bin/agent-browser")
PROFILE = str(Path.home() / ".hermes/chromium-brasil-profile")

# platform -> how many "next page" scrolls we do per account
DEFAULT_SCROLLS = {"tiktok": 10, "x": 12, "instagram": 8}

# API endpoints Zeeschuimer intercepts (response URL matchers)
CAPTURE_JS = r"""
window.__lgpt_cap = window.__lgpt_cap || [];
if (!window.__lgpt_hook) {
  window.__lgpt_hook = true;
  const orig = window.fetch;
  window.fetch = async (...args) => {
    const res = await orig(...args);
    const url = (typeof args[0] === 'string') ? args[0] : args[0].url;
    if (/api\.tiktokv\.com|www\.tiktok\.com\/api\/post\/item_list|x\.com\/i\/api\/graphql|www\.instagram\.com\/api\/v1/.test(url)) {
      try { const j = await res.clone().json(); window.__lgpt_cap.push({url: url, ts: Date.now(), data: j}); } catch (e) {}
    }
    return res;
  };
  const xo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, u, ...rest) {
    this.addEventListener('load', () => {
      try {
        if (/api\.tiktokv\.com|www\.tiktok\.com\/api\/post\/item_list|x\.com\/i\/api\/graphql|www\.instagram\.com\/api\/v1/.test(u)) {
          const ct = this.getResponseHeader && this.getResponseHeader('content-type') || '';
          if (ct.includes('json')) window.__lgpt_cap.push({url: String(u), ts: Date.now(), data: JSON.parse(this.responseText)});
        }
      } catch (e) {}
    });
    return xo.call(this, m, u, ...rest);
  };
}
"""


def ab(args: list[str], timeout: int = 120, headed: bool = False,
       profile: str = PROFILE) -> subprocess.CompletedProcess:
    """Run one agent-browser command against the persistent profile."""
    cmd = [AB, "--profile", profile]
    if headed:
        cmd.append("--headed")
    return subprocess.run(cmd + args, capture_output=True, text=True,
                          timeout=timeout)


def capture_account(platform: str, handle: str, url: str, out: Path,
                    scrolls: int, headed: bool) -> int:
    """Open one account page, scroll, harvest intercepted API responses."""
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_file = out / platform / handle / f"{day}.ndjson"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    ab(["open", url], headed=headed)
    time.sleep(6)
    # inject the interception hook once per page load
    ab(["eval", CAPTURE_JS], timeout=60)
    for i in range(scrolls):
        ab(["scroll", "down"], timeout=60)
        time.sleep(3)
        ab(["eval", CAPTURE_JS], timeout=60)  # SPA navigations reset hooks
    # harvest
    r = ab(["eval", "JSON.stringify(window.__lgpt_cap || [])"], timeout=90)
    raw = (r.stdout or "").strip()
    try:
        items = json.loads(json.loads(raw) if raw.startswith('"') else raw)
    except (json.JSONDecodeError, ValueError):
        items = []
    n = 0
    if items:
        with open(out_file, "a", encoding="utf-8") as fh:
            for it in items:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
    # reset the buffer for the next account
    ab(["eval", "window.__lgpt_cap = []"], timeout=60)
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Zeeschuimer autoscraper (Brazil 2026)")
    ap.add_argument("--accounts", default=str(Path(__file__).parent / "accounts.yaml"))
    ap.add_argument("--out", required=True, help="NDJSON output root (persistent storage)")
    ap.add_argument("--platforms", default="tiktok,x,instagram")
    ap.add_argument("--scrolls", type=int, default=None, help="override per-platform scroll count")
    ap.add_argument("--headed", action="store_true",
                    help="show the browser (use ONCE to log in to each platform)")
    ap.add_argument("--only-platform", default=None)
    ap.add_argument("--only-candidate", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.accounts, encoding="utf-8"))
    out = Path(args.out)
    platforms = args.platforms.split(",")

    for group in ("candidates", "parties"):
        for entity in cfg.get(group, []):
            name = entity["name"]
            if args.only_candidate and args.only_candidate.lower() not in name.lower():
                continue
            for platform in platforms:
                if not cfg["platforms"].get(platform, {}).get("enabled"):
                    continue
                if args.only_platform and platform != args.only_platform:
                    continue
                handles = entity["handles"].get(platform, [])
                scrolls = args.scrolls or DEFAULT_SCROLLS.get(platform, 10)
                for handle in handles:
                    for tpl in cfg["platforms"][platform]["base_urls"]:
                        url = tpl.format(handle=handle)
                        n = capture_account(platform, handle, url, out, scrolls, args.headed)
                        kind = "party" if group == "parties" else "candidate"
                        print(f"{name:20} {kind:9} {platform:10} @{handle:22} -> {n} API captures",
                              flush=True)
                        time.sleep(8)  # polite gap between accounts


if __name__ == "__main__":
    main()