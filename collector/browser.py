"""Browser/network capture drivers.

Layer 1 of the collector: navigate account pages and capture platform API
responses at the network layer. Firefox is the preferred long-running path;
these Chromium drivers remain useful for scripted/manual collection passes.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import websocket  # websocket-client

AB_BIN = str(Path.home() / ".hermes/hermes-agent/node_modules/.bin/agent-browser")
DEFAULT_PROFILE = str(Path.home() / ".hermes/chromium-laclaugpt-profile")
PLATFORM_API_MATCHERS = {
    "tiktok": r"api\.tiktokv\.com|/api/post/item_list|/api/search/(?:item_list|general/full)|/api/preload/item_list",
    "instagram": r"/api/v1/|/graphql(?:/query)?(?:[/?]|$)",
    "x": r"/i/api/graphql(?:/|\?|$)",
}


def capture_platform_url(platform: str, handle: str,
                         cfg_urls: Iterable[str]) -> list[str]:
    """Render configured base URLs for one handle."""
    return [template.format(handle=handle) for template in cfg_urls]


def _cdp_wall_timestamp(params: dict) -> str:
    """Convert CDP request wallTime to a real UTC timestamp.

    CDP `timestamp` is monotonic time and must never be persisted as a wall
    clock value. `wallTime` is seconds since the Unix epoch.
    """
    wall = params.get("wallTime")
    try:
        if wall is not None:
            return datetime.fromtimestamp(float(wall), timezone.utc).isoformat(
                timespec="milliseconds")
    except (TypeError, ValueError, OSError):
        pass
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class CDPCaptureDriver:
    """CDP Network-domain capture against a persistent browser profile."""

    name = "cdp"

    def __init__(self, profile: str = DEFAULT_PROFILE, ab_bin: str = AB_BIN,
                 scroll_pause: float = 3.0, settle: float = 8.0) -> None:
        self.profile = profile
        self.ab_bin = ab_bin
        self.scroll_pause = scroll_pause
        self.settle = settle
        # stats from the most recent capture_account call (api_requests /
        # bodies / empty_bodies) — surfaces silent capture failures
        self.last_stats: dict[str, int] = {"api_requests": 0, "bodies": 0,
                                           "empty_bodies": 0}

    def _ab(self, args: list[str], timeout: int = 120) -> str:
        result = subprocess.run(
            [self.ab_bin, "--profile", self.profile] + args,
            capture_output=True, text=True, timeout=timeout, check=False)
        return (result.stdout or "") + (result.stderr or "")

    def _ws_url(self) -> str:
        port_file = Path(self.profile) / "DevToolsActivePort"
        deadline = time.time() + 10
        while time.time() < deadline:
            if port_file.exists():
                lines = port_file.read_text(encoding="utf-8").split()
                if len(lines) >= 2:
                    return f"ws://127.0.0.1:{lines[0]}{lines[1]}"
            time.sleep(0.5)
        raise RuntimeError(f"no DevToolsActivePort under {self.profile}")

    def capture_account(self, platform: str, url: str, scrolls: int,
                        **_: Any) -> list[dict]:
        matcher = re.compile(PLATFORM_API_MATCHERS.get(platform, r"$^"))
        ws = websocket.create_connection(
            self._ws_url(), timeout=15, suppress_origin=True)
        captures: dict[str, dict] = {}
        bodies: list[dict] = []
        msg_id = 0

        def send(method: str, params: dict) -> int:
            nonlocal msg_id
            msg_id += 1
            ws.send(json.dumps({"id": msg_id, "method": method,
                                "params": params}))
            return msg_id

        try:
            target_call = send("Target.getTargets", {})
            targets = None
            ws.settimeout(10)
            while targets is None:
                message = json.loads(ws.recv())
                if message.get("id") == target_call and "result" in message:
                    targets = message["result"].get("targetInfos") or []

            page = next((target for target in targets
                         if target.get("type") == "page"
                         and urlparse(target.get("url") or "").hostname
                         and urlparse(target.get("url") or "").hostname.endswith(
                             ("tiktok.com", "instagram.com", "x.com"))), None)
            if page is None:
                page = next((target for target in targets
                             if target.get("type") == "page"
                             and not (target.get("url") or "").startswith("devtools")), None)
            if page is None:
                raise RuntimeError(
                    f"no page target for {url!r}; "
                    f"targets: {[target.get('url') for target in targets]}")

            attach_call = send("Target.attachToTarget", {
                "targetId": page["targetId"], "flatten": True})
            while True:
                message = json.loads(ws.recv())
                if message.get("id") == attach_call and "result" in message:
                    break
            session_id = message["result"]["sessionId"]

            def send_s(method: str, params: dict) -> int:
                nonlocal msg_id
                msg_id += 1
                ws.send(json.dumps({
                    "sessionId": session_id,
                    "id": msg_id,
                    "method": method,
                    "params": params,
                }))
                return msg_id

            def collect(message: dict) -> None:
                method = message.get("method", "")
                params = message.get("params") or {}
                if method == "Network.requestWillBeSent":
                    request = params.get("request") or {}
                    request_url = request.get("url", "")
                    if matcher.search(request_url):
                        request_id = params.get("requestId")
                        if request_id:
                            captures[request_id] = {
                                "url": request_url,
                                "ts": _cdp_wall_timestamp(params),
                                "finished": False,
                            }
                elif method == "Network.loadingFinished":
                    request_id = params.get("requestId")
                    if request_id in captures:
                        captures[request_id]["finished"] = True
                elif method == "Network.loadingFailed":
                    request_id = params.get("requestId")
                    if request_id in captures:
                        captures[request_id]["failed"] = True

            send_s("Network.enable", {})
            time.sleep(0.3)

            # A background thread reads the shared socket for the whole
            # navigation (open + settle + every scroll). Draining only
            # after the fact loses the item_list requests: they are
            # emitted during navigation, not after the last scroll.
            reading = threading.Event()
            reading.set()

            def read_events() -> None:
                ws.settimeout(0.5)
                while reading.is_set():
                    try:
                        message = json.loads(ws.recv())
                    except (websocket.WebSocketTimeoutException, OSError):
                        continue
                    collect(message)

            reader = threading.Thread(target=read_events, daemon=True)
            reader.start()

            self._ab(["open", url])
            time.sleep(self.settle)
            for _ in range(scrolls):
                self._ab(["scroll", "down"])
                time.sleep(self.scroll_pause)
            time.sleep(2.0)  # let trailing API responses reach loadingFinished

            reading.clear()
            reader.join(timeout=5)

            for request_id, meta in captures.items():
                if meta.get("failed") or not meta.get("finished"):
                    continue
                call = send_s("Network.getResponseBody", {"requestId": request_id})
                got: dict | None = None
                ws.settimeout(10)
                while got is None:
                    try:
                        message = json.loads(ws.recv())
                    except (websocket.WebSocketTimeoutException, OSError):
                        break
                    if message.get("id") == call:
                        got = message
                if not got or "result" not in got:
                    self.last_stats["empty_bodies"] += 1
                    continue
                body = got["result"].get("body", "")
                if got["result"].get("base64Encoded"):
                    body = base64.b64decode(body).decode("utf-8", "replace")
                try:
                    parsed = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    self.last_stats["empty_bodies"] += 1
                    continue
                self.last_stats["bodies"] += 1
                bodies.append({
                    "url": meta["url"],
                    "data": parsed,
                    "ts": meta["ts"],
                    "platform_url": url,
                })
        finally:
            reading.clear()
            try:
                ws.close()
            except OSError:
                pass
        self.last_stats["api_requests"] = len(captures)
        return bodies


class AgentBrowserDriver:
    """HAR-export fallback; some browser stacks omit response bodies."""

    name = "agent-browser"

    def __init__(self, profile: str = DEFAULT_PROFILE, ab_bin: str = AB_BIN,
                 scroll_pause: float = 3.0, settle: float = 8.0) -> None:
        self.profile = profile
        self.ab_bin = ab_bin
        self.scroll_pause = scroll_pause
        self.settle = settle

    def _ab(self, args: list[str], timeout: int = 120) -> str:
        result = subprocess.run(
            [self.ab_bin, "--profile", self.profile] + args,
            capture_output=True, text=True, timeout=timeout, check=False)
        return (result.stdout or "") + (result.stderr or "")

    def capture_account(self, platform: str, url: str, scrolls: int,
                        **_: Any) -> list[dict]:
        import tempfile

        with tempfile.NamedTemporaryFile(prefix="lgpt-", suffix=".har",
                                         delete=False) as temp:
            har = temp.name
        self._ab(["network", "har", "start", har])
        self._ab(["open", url])
        time.sleep(self.settle)
        for _ in range(scrolls):
            self._ab(["scroll", "down"])
            time.sleep(self.scroll_pause)
        output = self._ab(["network", "har", "stop"])
        saved = self._har_path(output) or har
        try:
            har_data = json.loads(Path(saved).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        matcher = re.compile(PLATFORM_API_MATCHERS.get(platform, r"$^"))
        captures: list[dict] = []
        for entry in har_data.get("log", {}).get("entries", []):
            request_url = entry.get("request", {}).get("url", "")
            if not matcher.search(request_url):
                continue
            body = entry.get("response", {}).get("content", {})
            text = body.get("text") or ""
            if not text:
                captures.append({
                    "url": request_url,
                    "data": None,
                    "ts": entry.get("startedDateTime", ""),
                    "platform_url": url,
                })
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            captures.append({
                "url": request_url,
                "data": parsed,
                "ts": entry.get("startedDateTime", ""),
                "platform_url": url,
            })
        return captures

    @staticmethod
    def _har_path(stop_output: str) -> str | None:
        for token in stop_output.splitlines():
            token = token.strip()
            if token.endswith(".har") and ("/" in token or "\\" in token):
                return token
        return None
