"""Tests for x-marketing/lib/url_parser.py. Not shipped with the installed skill.

Run from the repo root:  python3 tests/test_url_parser.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "x-marketing"))
from lib.url_parser import parse_x_url  # noqa: E402


def main() -> int:
    # Hosts that are not X, or only mention an X host in the path, must stay "unknown".
    not_x = [
        "https://vxtwitter.com/someone/status/1790000000000000000",
        "https://fxtwitter.com/someone/status/1790000000000000000",
        "https://mytwitter.com/someone/status/1790000000000000000",
        "https://example.org/twitter.com/x/status/1790000000000000000",
        "https://example.org/x.com/levelsio",
    ]
    for url in not_x:
        assert parse_x_url(url)["url_type"] == "unknown", f"non-X host parsed as X: {url}"

    assert parse_x_url("https://x.com/paulg/status/1790000000000000000?s=20") == {
        "handle": "paulg",
        "tweet_id": "1790000000000000000",
        "url_type": "tweet",
        "canonical_url": "https://x.com/paulg/status/1790000000000000000",
    }
    assert parse_x_url("https://mobile.twitter.com/naval/status/1002103360646823936")["url_type"] == "tweet"
    assert parse_x_url("https://x.com/i/web/status/1790000000000000000")["handle"] is None
    assert parse_x_url("https://x.com/levelsio")["url_type"] == "profile"
    assert parse_x_url("twitter.com/jack")["url_type"] == "profile"
    assert parse_x_url("https://x.com/explore")["url_type"] == "unknown"
    assert parse_x_url("1790000000000000000")["url_type"] == "tweet"
    print("OK: url_parser rejects non-X hosts and parses real X URLs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
