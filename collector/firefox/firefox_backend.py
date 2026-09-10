"""Firefox capture backend for the LaclauGPT social-media collector.

The Firefox extension captures public platform API response bodies and POSTs
raw captures here. This backend is deliberately boring: validate the study
window, parse platform payloads, normalise records, and persist raw + derived
representations through the shared collector Store.

Run:
    python -m collector.firefox.firefox_backend \
        --config collector/config/study.private.yaml \
        --data-root ~/laclaugpt-brasil-data
"""
from __future__ import annotations

import argparse
import json
import subprocess
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .. import COLLECTOR_VERSION, normalize
from ..config import load_config
from ..modules import PLATFORM_MODULES
from ..store import Store, utc_stamp

REPO_ROOT = Path(__file__).resolve().parents[2]
_git_commit_cache: str | None = None


def git_commit(repo: Path = REPO_ROOT) -> str:
    global _git_commit_cache
    if _git_commit_cache is None:
        try:
            _git_commit_cache = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"], cwd=repo,
                capture_output=True, text=True, timeout=15,
                check=False).stdout.strip()
        except Exception:  # noqa: BLE001
            _git_commit_cache = ""
    return _git_commit_cache


class CaptureServer(ThreadingHTTPServer):
    """HTTP endpoints: /capture (POST), /tour, /status (GET), /ping (POST)."""

    def __init__(self, config_path: str, data_root: str,
                 host: str = "127.0.0.1", port: int = 8765) -> None:
        self.cfg = load_config(config_path)
        self.store = Store(Path(data_root))
        self.repo = REPO_ROOT
        self.stats = {"captures": 0, "posts": 0, "errors": 0, "skipped": 0}
        self.run_id = utc_stamp()
        self.lock = threading.RLock()
        self._tz = self._load_timezone(self.cfg.timezone)
        super().__init__((host, port), Handler)
        print(
            f"firefox backend ready: {len(self.cfg.accounts())} accounts, "
            f"window {self.cfg.start}..{self.cfg.end} ({self.cfg.timezone}), "
            f"data root {data_root}",
            flush=True,
        )

    @staticmethod
    def _load_timezone(name: str):
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            print(
                f"warning: timezone {name!r} not available; using UTC. "
                "Install the Python 'tzdata' package on platforms without an IANA database.",
                flush=True,
            )
            return timezone.utc

    def local_today(self):
        return datetime.now(self._tz).date()

    def active(self) -> bool:
        return self.cfg.in_window(self.local_today())

    def tour_accounts(self) -> list[dict]:
        """Return one navigation row per configured account page URL."""
        if not self.active():
            return []
        rows: list[dict] = []
        for account in self.cfg.accounts():
            templates = self.cfg.platform_urls.get(account["platform"], [])
            urls = [tpl.format(handle=account["handle"]) for tpl in templates]
            if not urls:
                urls = [""]
            for url in urls:
                rows.append({**account, "url": url})
        return rows


class Handler(BaseHTTPRequestHandler):
    server: CaptureServer

    def log_message(self, fmt, *args):  # quiet local service
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"

        if path == "/ping":
            self._json(200, {
                "ok": True,
                "collector": COLLECTOR_VERSION,
                "active": self.server.active(),
            })
            return
        if path != "/capture":
            self._json(404, {"error": "not found"})
            return

        if not self.server.active():
            with self.server.lock:
                self.server.stats["skipped"] += 1
            self._json(200, {
                "ok": True,
                "skipped": "outside study window",
                "date": str(self.server.local_today()),
            })
            return

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"error": "bad json"})
            return

        platform = data.get("platform", "")
        if platform not in PLATFORM_MODULES:
            self._json(400, {"error": f"unsupported platform: {platform!r}"})
            return

        with self.server.lock:
            self.server.stats["captures"] += 1
        try:
            new_posts = self._process_capture(data)
            self._json(200, {
                "ok": True,
                "new_posts": new_posts,
                "posts_total": self.server.stats["posts"],
            })
        except Exception as exc:  # noqa: BLE001
            with self.server.lock:
                self.server.stats["errors"] += 1
            self._json(500, {"error": str(exc)[:300]})

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/tour":
            cfg = self.server.cfg
            self._json(200, {
                "active": self.server.active(),
                "date": str(self.server.local_today()),
                "accounts": self.server.tour_accounts(),
                "window": {"start": str(cfg.start), "end": str(cfg.end)},
                "timezone": cfg.timezone,
            })
        elif path == "/status":
            self._json(200, {
                "collector": COLLECTOR_VERSION,
                "git_commit": git_commit(self.server.repo),
                "run_id": self.server.run_id,
                "active": self.server.active(),
                "date": str(self.server.local_today()),
                "stats": dict(self.server.stats),
                "seen_total": self.server.store.seen_count(),
            })
        else:
            self._json(404, {"error": "not found"})

    @staticmethod
    def _decode_platform_body(body):
        """Accept JSON objects or common JSON response prefixes."""
        if isinstance(body, (dict, list)):
            return body
        if not isinstance(body, str):
            raise ValueError("capture body is not text or JSON")
        text = body.lstrip("\ufeff \t\r\n")
        if text.startswith("for (;;);"):
            text = text[len("for (;;);"):].lstrip()
        # Some APIs use an anti-XSSI prefix before the real JSON payload.
        if text.startswith(")]}'"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:].lstrip(", \t\r\n")
        return json.loads(text)

    # -- capture -> parse -> normalise -> store -------------------------

    def _process_capture(self, data: dict) -> int:
        platform = data.get("platform", "")
        module = PLATFORM_MODULES[platform]
        api_url = data.get("api_url", "")
        platform_url = data.get("platform_url", "") or api_url
        captured_at = data.get("captured_at", "") or datetime.now(
            timezone.utc).isoformat(timespec="seconds")
        body = data.get("body")
        if body in (None, ""):
            return 0

        payload = self._decode_platform_body(body)
        meta = {
            "captured_at": captured_at,
            "collector_version": COLLECTOR_VERSION,
            "git_commit": git_commit(self.server.repo),
            "source_platform_url": platform_url,
            "source_url": api_url,
            "run_id": self.server.run_id,
            "account": self._account_for(platform, platform_url),
        }

        with self.server.lock:
            raw_ref = self.server.store.append_raw(platform, {
                "url": api_url,
                "ts": captured_at,
                "platform_url": platform_url,
                "data": payload,
            })
            new_posts = 0
            for item in module.capture(payload, platform_url, api_url):
                mapped = module.map_item(item, meta)
                record = normalize.normalise(platform, mapped, item, meta)
                record["raw_ref"] = raw_ref
                if self.server.store.upsert_post(record, raw_ref):
                    new_posts += 1
            self.server.stats["posts"] += new_posts
        return new_posts

    def _account_for(self, platform: str, platform_url: str) -> str:
        """Resolve the configured target from a visited profile/page URL."""
        try:
            segments = [segment.lstrip("@").casefold()
                        for segment in urlparse(platform_url).path.split("/")
                        if segment]
        except ValueError:
            segments = []
        for row in self.server.cfg.accounts():
            if row["platform"] != platform:
                continue
            if str(row["handle"]).casefold() in segments:
                return f"{row['name']}:{row['handle']}"
        return "unattributed"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m collector.firefox.firefox_backend")
    ap.add_argument("--config", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    server = CaptureServer(args.config, args.data_root, host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.store.write_manifest({
            "study": server.cfg.study,
            "collector_version": COLLECTOR_VERSION,
            "git_commit": git_commit(server.repo),
            "run_id": server.run_id,
            "stats": dict(server.stats),
            "seen_total": server.store.seen_count(),
            "missing_candidates": server.cfg.missing_candidates(),
            "window": {"start": str(server.cfg.start), "end": str(server.cfg.end)},
            "timezone": server.cfg.timezone,
            "run_finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        server.store.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
