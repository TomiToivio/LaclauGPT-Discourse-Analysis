"""Shared synthetic fixtures for collector tests.

Sanitised synthetic platform payloads only; no real research data. Shapes mirror
platform payloads consumed by the LaclauGPT-native parsers.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture
def tiktok_item() -> dict:
    return load_fixture("tiktok_item.json")


@pytest.fixture
def tiktok_api_response(tiktok_item: dict) -> dict:
    return {"statusCode": 0, "itemList": [tiktok_item], "cursor": 0}


@pytest.fixture
def instagram_itemlist_item() -> dict:
    return load_fixture("instagram_itemlist_item.json")


@pytest.fixture
def instagram_polaris_item() -> dict:
    return load_fixture("instagram_polaris_item.json")


@pytest.fixture
def instagram_reel_item() -> dict:
    return load_fixture("instagram_reel_item.json")


@pytest.fixture
def x_modern_tweet() -> dict:
    return load_fixture("x_tweet_modern.json")


@pytest.fixture
def x_legacy_tweet() -> dict:
    return load_fixture("x_tweet_legacy.json")


@pytest.fixture
def x_graphql_envelope(x_modern_tweet: dict) -> dict:
    """Minimal TimelineAddEntries envelope like X's GraphQL responses."""
    return {
        "data": {
            "user": {
                "result": {
                    "timeline_v2": {
                        "timeline": {
                            "instructions": [{
                                "type": "TimelineAddEntries",
                                "entries": [{
                                    "entryId": f"tweet-{x_modern_tweet['rest_id']}",
                                    "content": {
                                        "entryType": "TimelineTimelineItem",
                                        "__typename": "TimelineTimelineItem",
                                        "itemContent": {
                                            "itemType": "TimelineTweet",
                                            "__typename": "TimelineTweet",
                                            "tweet_results": {"result": x_modern_tweet},
                                        },
                                    },
                                }],
                            }]
                        }
                    }
                }
            }
        }
    }
