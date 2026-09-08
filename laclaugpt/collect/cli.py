"""CLI: laclaugpt collect {rss|web|manual|hermes|telegram} — one canonical spine."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from laclaugpt.collect import (CollectionStore, COLLECTOR_VERSION,
                               collect_hermes, collect_manual, collect_rss,
                               collect_telegram_message, collect_web)
from laclaugpt.model import utcnow


def register(sub) -> None:
    """Attach `collect` subcommands to the laclaugpt CLI parser."""
    collect = sub.add_parser("collect",
                             help="collect sources into the canonical corpus")
    csub = collect.add_subparsers(dest="collect_target", required=True)

    rss = csub.add_parser("rss", help="collect RSS/Atom feeds")
    rss.add_argument("feeds", nargs="+",
                     help="feed URLs or a config file with one URL per line")
    rss.add_argument("--fetch-article", action="store_true",
                     help="also fetch the linked article page")

    web = csub.add_parser("web", help="fetch plain web pages")
    web.add_argument("urls", nargs="+", help="URLs to fetch")
    web.add_argument("--urls-file", help="file with one URL per line")

    manual = csub.add_parser("manual", help="human-researcher submission")
    manual.add_argument("--url")
    manual.add_argument("--text")
    manual.add_argument("--file")
    manual.add_argument("--title")
    manual.add_argument("--author")
    manual.add_argument("--notes")

    hermes = csub.add_parser("hermes", help="Hermes Agent JSON submission")
    hermes.add_argument("payload", help="JSON file or '-' for stdin")

    telegram = csub.add_parser("telegram",
                               help="normalize one Vasama-OSINT Telegram event (JSON)")
    telegram.add_argument("payload", help="JSON file or '-' for stdin")

    minet = csub.add_parser("minet",
                            help="import a minet CSV (extract or collector output)")
    minet.add_argument("csv_path")
    minet.add_argument("--kind", choices=("extract", "collector"),
                       default="extract", help="minet output type")
    minet.add_argument("--platform", help="platform tag for collector CSVs")
    minet.add_argument("--text-column")
    minet.add_argument("--url-column")
    minet.add_argument("--author-column")
    minet.add_argument("--timestamp-column")

    zeeschuimer = csub.add_parser(
        "zeeschuimer",
        help="import a Zeeschuimer NDJSON export (browser capture)")
    zeeschuimer.add_argument("ndjson_path")
    zeeschuimer.add_argument("--text-fields",
                             help="comma-separated probe keys for text extraction")
    zeeschuimer.add_argument("--platform", help="platform tag override")


def _urls_from_file(path: str) -> list[str]:
    return [u.strip() for u in Path(path).read_text(encoding="utf-8").splitlines()
            if u.strip() and not u.strip().startswith("#")]


def _read_payload(path: str) -> dict:
    if path == "-":
        return json.load(__import__("sys").stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> int:
    store = CollectionStore()
    saved = skipped = 0

    if args.collect_target == "rss":
        records = []
        for feed in args.feeds:
            if feed.startswith("http"):
                records.extend(collect_rss(feed, fetch_article=args.fetch_article))
            else:
                for feed_url in _urls_from_file(feed):
                    records.extend(collect_rss(feed_url,
                                               fetch_article=args.fetch_article))
        saved, skipped = store.save_many(records)

    elif args.collect_target == "web":
        urls = list(args.urls)
        if args.urls_file:
            urls.extend(_urls_from_file(args.urls_file))
        records = []
        for url in urls:
            try:  # network fetch outside the pure function
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": "LaclauGPT-collect"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    records.append(collect_web(url, html_text=resp.read().decode(
                        "utf-8", errors="replace"), http_status=resp.status))
            except Exception as exc:  # recorded as skipped, never fatal
                print(json.dumps({"skipped": url, "reason": str(exc)}))
        saved, skipped = store.save_many(records)

    elif args.collect_target == "manual":
        saved, skipped = store.save_many([collect_manual(
            url=args.url, text=args.text, title=args.title, author=args.author,
            file_path=args.file, notes=args.notes)])

    elif args.collect_target == "hermes":
        records = collect_hermes(_read_payload(args.payload))
        saved, skipped = store.save_many(records)

    elif args.collect_target == "telegram":
        saved, skipped = store.save_many(
            [collect_telegram_message(_read_payload(args.payload))])

    elif args.collect_target == "minet":
        from laclaugpt.collect.minet_zeeschuimer import (
            collect_minet_collector, collect_minet_extract)
        if args.kind == "collector":
            records = collect_minet_collector(
                args.csv_path, platform=args.platform or "unknown",
                text_column=args.text_column)
        else:
            records = collect_minet_extract(
                args.csv_path, text_column=args.text_column,
                url_column=args.url_column, author_column=args.author_column,
                timestamp_column=args.timestamp_column)
        saved, skipped = store.save_many(records)

    elif args.collect_target == "zeeschuimer":
        from laclaugpt.collect.minet_zeeschuimer import collect_zeeschuimer
        text_fields = (tuple(t.strip() for t in args.text_fields.split(","))
                       if args.text_fields else None)
        records = collect_zeeschuimer(
            args.ndjson_path,
            text_fields=text_fields if text_fields is not None
            else ("desc", "caption", "text", "content", "title", "body",
                  "full_text"),
            platform_hint=args.platform)
        saved, skipped = store.save_many(records)

    print(json.dumps({"collector_version": COLLECTOR_VERSION,
                      "saved": saved, "skipped_duplicates": skipped}))
    return 0