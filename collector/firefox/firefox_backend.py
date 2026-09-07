"""Firefox capture backend for the LaclauGPT Brazil collector.

The Firefox extension (collector/firefox/extension/) captures platform
API response BODIES via webRequest.filterResponseData — the only
reliable body-capture API, and the reason this collector runs on
Firefox (Chromium's CDP/HAR paths return empty bodies for the main
TikTok feed, verified 2026-09-07). The extension POSTs raw captures
here; this backend runs the SAME tested Zeeschuimer-derived parsers
(collector/modules) and the SAME durable store (collector/store.py)
as the CDP driver, so all capture paths converge on one pipeline.

Also serves the tour (account list from the study YAML) to the
extension's navigation layer and writes the collection manifest.

Run:
    python -m collector.firefox.firefox_backend \
        --config collector/config/brazil-election-2026.yaml \
        --data-root ~/laclaugpt-brasil-data

Academic research use only.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .. import COLLECTOR_VERSION, normalize
from ..config import load_config
from ..modules import PLATFORM_MODULES
from ..store import Store, utc_stamp

_git_commit_cache: str | None = None


def git_commit(repo: Path) -> str:
    global _git_commit_cache
    if _git_commit_cache is None:
        try:
            _git_commit_cache = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                capture_output=True, text=True, timeout=15).stdout.strip()
        except Exception:  # noqa: BLE001
            _git_commit_cache = ""
    return _git_commit_cache


class CaptureServer(ThreadingHTTPServer):
    """HTTP endpoints: /capture (POST), /tour (GET), /ping (POST)."""

    def __init__(self, config_path: str, data_root: str,
                 host: str = "127.0.0.1", port: int = 8765) -> None:
        self.cfg = load_config(config_path)
        self.store = Store(Path(data_root))
        self.repo = Path.cwd()
        self.stats = {"captures": 0, "posts": 0, "errors": 0}
        self.run_id = utc_stamp()
        self.lock = threading.Lock()
        super().__init__((host, port), Handler)
        print(f"firefox backend ready: {len(self.cfg.accounts())} accounts, "
              f"window {self.cfg.start}..{self.cfg.end}, "
              f"data root {data_root}", flush=True)


class Handler(BaseHTTPRequestHandler):
    server: CaptureServer

    def log_message(self, fmt, *args):  # quiet
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if self.path == "/ping":
            self._json(200, {"ok": True, "collector": COLLECTOR_VERSION})
            return
        if self.path != "/capture":
            self._json(404, {"error": "not found"})
            return
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._json(400, {"error": "bad json"})
            return
        self.server.stats["captures"] += 1
        try:
            self._process_capture(data)
            self._json(200, {"ok": True,
                             "posts": self.server.stats["posts"]})
        except Exception as exc:  # noqa: BLE001
            self.server.stats["errors"] += 1
            self._json(500, {"error": str(exc)[:200]})

    def do_GET(self):
        if self.path == "/tour":
            cfg = self.server.cfg
            self._json(200, {
                "accounts": cfg.accounts(),
                "index": 0,
                "window": {"start": str(cfg.start), "end": str(cfg.end)},
            })
        elif self.path == "/status":
            self._json(200, {
                "collector": COLLECTOR_VERSION,
                "git_commit": git_commit(self.server.repo),
                "run_id": self.server.run_id,
                "stats": self.server.stats,
                "seen_total": self.server.store.seen_count(),
            })
        else:
            self._json(404, {"error": "not found"})

    # -- the pipeline: capture -> parse -> normalise -> store -------------

    def _process_capture(self, data: dict) -> None:
        platform = data.get("platform", "")
        module = PLATFORM_MODULES.get(platform)
        if module is None:
            return
        api_url = data.get("api_url", "")
        platform_url = data.get("platform_url", "") or api_url
        captured_at = data.get("captured_at", "") or datetime.now(
            timezone.utc).isoformat(timespec="seconds")
        body = data.get("body")
        if not body:
            return
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return

        meta = {
            "captured_at": captured_at,
            "collector_version": COLLECTOR_VERSION,
            "git_commit": git_commit(self.server.repo),
            "source_platform_url": platform_url,
            "source_url": api_url,
            "run_id": self.server.run_id,
            "account": self._account_for(platform, platform_url),
        }
        raw_ref = self.server.store.append_raw(platform, {
            "url": api_url, "ts": captured_at,
            "platform_url": platform_url, "data": payload})

        with self.server.lock:
            for item in module.capture(payload, platform_url, api_url):
                mapped = module.map_item(item, meta)
                record = normalize.normalise(platform, mapped, item, meta)
                record["raw_ref"] = raw_ref
                if self.server.store.upsert_post(record, raw_ref):
                    self.server.stats["posts"] += 1

    def _account_for(self, platform: str, platform_url: str) -> str:
        """Resolve which configured account (if any) was visited."""
        for row in self.server.cfg.accounts():
            if row["platform"] != platform:
                continue
            if f"/{row['handle']}" in (platform_url or "").lower():
                return f"{row['name']}:{row['handle']}"
        return "unattributed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m collector.firefox.firefox_backend")
    ap.add_argument("--config", required=True)
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args(argv)
    server = CaptureServer(args.config, args.data_root)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # write the run manifest on shutdown
        server.store.write_manifest({
            "study": server.cfg.study,
            "collector_version": COLLECTOR_VERSION,
            "git_commit": git_commit(server.repo),
            "run_id": server.run_id,
            "stats": server.stats,
            "seen_total": server.store.seen_count(),
            "missing_candidates": server.cfg.missing_candidates(),
            "run_finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        server.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())