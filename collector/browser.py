"""Browser/network capture drivers.

Layer 1 of the collector: navigate account pages and capture platform
API responses at the network layer. Drivers are pluggable; parsing never
depends on one automation framework (issue #20 requirement).

Primary driver: CDPCaptureDriver. It attaches to the browser's DevTools
protocol endpoint (DevToolsActivePort of a persistent logged-in profile),
subscribes to Network events, and fetches each matching JSON response
body with Network.getResponseBody — the same data Zeeschuimer's extension
grabs, captured from outside the page. Navigation and scrolling are
driven through the agent-browser CLI.

A HAR-export fallback (AgentBrowserDriver) is included for environments
where CDP attachment is unavailable; note that HAR exports may omit
response bodies depending on the automation stack.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import websocket  # websocket-client

AB_BIN = str(Path.home() / ".hermes/hermes-agent/node_modules/.bin/agent-browser")
DEFAULT_PROFILE = str(Path.home() / ".hermes/chromium-laclaugpt-profile")
PLATFORM_API_MATCHERS = {
    "tiktok": r"api\.tiktokv\.com|/api/post/item_list|/api/search/item_list|/api/preload/item_list",
    "instagram": r"/api/v1/|/graphql/query",
    "x": r"/i/api/graphql",
}


def capture_platform_url(platform: str, handle: str, cfg_urls: Iterable[str]) -> list[str]:
    """Render configured base URLs for one handle."""
    return [tpl.format(handle=handle) for tpl in cfg_urls]


class CDPCaptureDriver:
    """CDP Network-domain capture against a persistent browser profile."""

    name = "cdp"

    def __init__(self, profile: str = DEFAULT_PROFILE, ab_bin: str = AB_BIN,
                 scroll_pause: float = 3.0, settle: float = 8.0) -> None:
        self.profile = profile
        self.ab_bin = ab_bin
        self.scroll_pause = scroll_pause
        self.settle = settle

    def _ab(self, args: list[str], timeout: int = 120) -> str:
        r = subprocess.run([self.ab_bin, "--profile", self.profile] + args,
                           capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")

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
        """Visit one page, scroll, return parsed captures [{url,data,ts,...}]."""
        matcher = re.compile(PLATFORM_API_MATCHERS.get(platform, r"$^"))
        ws = websocket.create_connection(self._ws_url(), timeout=15,
                                         suppress_origin=True)
        captures: dict[str, dict] = {}  # requestId -> {url, ts}
        bodies: list[dict] = []
        msg_id = 0

        def send(method: str, params: dict) -> int:
            nonlocal msg_id
            msg_id += 1
            ws.send(json.dumps({"id": msg_id, "method": method,
                                "params": params}))
            return msg_id

        def drain(seconds: float, handle) -> None:
            end = time.time() + seconds
            ws.settimeout(0.5)
            while time.time() < end:
                try:
                    m = json.loads(ws.recv())
                except (websocket.WebSocketTimeoutException, OSError):
                    continue
                handle(m)

        def on_event(m: dict) -> None:
            method = m.get("method", "")
            if method == "Network.requestWillBeSent":
                req = m["params"]["request"]
                rid = m["params"]["requestId"]
                if matcher.search(req.get("url", "")):
                    captures[rid] = {"url": req["url"],
                                     "ts": m["params"].get("timestamp", "")}

        try:
            # browser-level socket: attach to the page target first,
            # then subscribe to Network on the attached session
            send("Target.getTargets", {})
            targets = None
            ws.settimeout(10)
            while targets is None:
                m = json.loads(ws.recv())
                if m.get("id") == 1 and "result" in m:
                    targets = m["result"].get("targetInfos") or []
            page = next((t for t in targets
                         if t.get("type") == "page"
                         and urlparse(t.get("url") or "").hostname
                         and urlparse(t.get("url") or "").hostname.endswith(
                             ("tiktok.com", "instagram.com", "x.com"))), None)
            if page is None:
                # fall back to the first non-devtools page target
                page = next((t for t in targets
                             if t.get("type") == "page"
                             and not (t.get("url") or "").startswith("devtools")), None)
            if page is None:
                raise RuntimeError(f"no page target for {url!r}; "
                                   f"targets: {[t.get('url') for t in targets]}")
            session = page["targetId"]
            send("Target.attachToTarget", {"targetId": session,
                                           "flatten": True})
            # wait for attach ack
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == msg_id and "result" in m:
                    break
            session_id = m["result"]["sessionId"]

            def send_s(method: str, params: dict) -> int:
                nonlocal msg_id
                msg_id += 1
                ws.send(json.dumps({"sessionId": session_id, "id": msg_id,
                                    "method": method, "params": params}))
                return msg_id

            send_s("Network.enable", {})
            time.sleep(0.3)

            self._ab(["open", url])
            time.sleep(self.settle)
            for _ in range(scrolls):
                self._ab(["scroll", "down"])
                time.sleep(self.scroll_pause)

            # collect request events after the event subscription
            def collect(m: dict) -> None:
                if m.get("method") != "Network.requestWillBeSent":
                    return
                req = m["params"]["request"]
                rid = m["params"]["requestId"]
                if matcher.search(req.get("url", "")):
                    captures[rid] = {"url": req["url"],
                                     "ts": m["params"].get("timestamp", "")}

            drain(2.0, collect)
            for rid, meta in captures.items():
                call = send_s("Network.getResponseBody", {"requestId": rid})
                got: dict | None = None
                ws.settimeout(10)
                while got is None:
                    try:
                        m = json.loads(ws.recv())
                    except (websocket.WebSocketTimeoutException, OSError):
                        break
                    if m.get("id") == call:
                        got = m
                if not got or "result" not in got:
                    continue
                body = got["result"].get("body", "")
                if got["result"].get("base64Encoded"):
                    body = base64.b64decode(body).decode("utf-8", "replace")
                try:
                    parsed = json.loads(body)
                except (json.JSONDecodeError, TypeError):
                    continue
                bodies.append({"url": meta["url"], "data": parsed,
                               "ts": meta["ts"], "platform_url": url})
        finally:
            try:
                ws.close()
            except OSError:
                pass
        return bodies


class AgentBrowserDriver:
    """HAR-export fallback (no response bodies in some stacks)."""

    name = "agent-browser"

    def __init__(self, profile: str = DEFAULT_PROFILE, ab_bin: str = AB_BIN,
                 scroll_pause: float = 3.0, settle: float = 8.0) -> None:
        self.profile = profile
        self.ab_bin = ab_bin
        self.scroll_pause = scroll_pause
        self.settle = settle

    def _ab(self, args: list[str], timeout: int = 120) -> str:
        r = subprocess.run([self.ab_bin, "--profile", self.profile] + args,
                           capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")

    def capture_account(self, platform: str, url: str, scrolls: int,
                        **_: Any) -> list[dict]:
        import tempfile

        har = tempfile.mktemp(prefix="lgpt-", suffix=".har")
        self._ab(["network", "har", "start", har])
        self._ab(["open", url])
        time.sleep(self.settle)
        for _ in range(scrolls):
            self._ab(["scroll", "down"])
            time.sleep(self.scroll_pause)
        out = self._ab(["network", "har", "stop"])
        saved = self._har_path(out) or har
        try:
            har_data = json.loads(Path(saved).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        matcher = re.compile(PLATFORM_API_MATCHERS.get(platform, r"$^"))
        captures: list[dict] = []
        for entry in har_data.get("log", {}).get("entries", []):
            req_url = entry.get("request", {}).get("url", "")
            if not matcher.search(req_url):
                continue
            body = entry.get("response", {}).get("content", {})
            text = body.get("text") or ""
            if not text:
                captures.append({"url": req_url, "data": None,
                                 "ts": entry.get("startedDateTime", ""),
                                 "platform_url": url})
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            captures.append({"url": req_url, "data": parsed,
                             "ts": entry.get("startedDateTime", ""),
                             "platform_url": url})
        return captures

    @staticmethod
    def _har_path(stop_output: str) -> str | None:
        for token in stop_output.splitlines():
            token = token.strip()
            if token.endswith(".har") and "/" in token:
                return token
        return None