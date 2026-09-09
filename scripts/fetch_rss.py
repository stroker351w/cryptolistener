#!/usr/bin/env python3
"""Pull the configured crypto news RSS feeds and normalize them into a
single list of articles. Any single feed failing (timeout, HTTP error,
malformed XML, site blocking us) is logged and skipped -- it never takes
the whole run down.
"""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import USER_AGENT, load_json, parse_date, parse_feed  # noqa: E402
from relevance import is_relevant  # noqa: E402
from classify import classify  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# Verified live as of 2026-09-03. If a source goes dark, drop it here
# rather than letting it fail loudly on every scheduled run.
SOURCES = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "The Block": "https://www.theblock.co/rss.xml",
    "Bitcoin Magazine": "https://bitcoinmagazine.com/feed",
    "CryptoSlate": "https://cryptoslate.com/feed/",
    "The Defiant": "https://thedefiant.io/feed",
    "Blockworks": "https://blockworks.co/feed",
    "U.Today": "https://u.today/rss",
    "NewsBTC": "https://www.newsbtc.com/feed/",
    "CryptoPotato": "https://cryptopotato.com/feed/",
    "SEC Press Releases": "https://www.sec.gov/news/pressreleases.rss",
}

MAX_PER_SOURCE = 15
REQUEST_TIMEOUT = 15


def fetch_source(name: str, url: str):
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [skip] {name}: {exc}", file=sys.stderr)
        return []

    entries = parse_feed(resp.text)
    if not entries:
        print(f"  [skip] {name}: feed parsed but had no items", file=sys.stderr)
        return []

    articles = []
    for entry in entries[:MAX_PER_SOURCE]:
        dt = parse_date(entry["published"])
        articles.append(
            {
                "source": name,
                "title": entry["title"],
                "link": entry["link"],
                "summary": entry["summary"],
                "published": dt.isoformat() if dt else None,
                "relevant": is_relevant(entry["title"], entry["summary"]),
                "category": classify(entry["title"], entry["summary"]),
            }
        )
    print(f"  [ok]   {name}: {len(articles)} articles")
    return articles


def main():
    print(f"Fetching {len(SOURCES)} RSS sources...")

    # Some feeds (The Defiant, confirmed) re-stamp an item's <pubDate> to
    # the feed-generation time on every single request instead of its
    # real publish time -- verified by fetching the feed twice and
    # watching the date shift to match each fetch. Left unchecked, that
    # makes the same story look "0m ago" and re-sort to the top forever.
    # Fix: trust a source's reported date only the first time we see a
    # given link; after that, keep whatever we recorded originally.
    previous = load_json(DATA_DIR / "news.json", [])
    first_seen_published = {
        a["link"]: a["published"] for a in previous if a.get("link") and a.get("published")
    }

    all_articles = []
    for name, url in SOURCES.items():
        all_articles.extend(fetch_source(name, url))
        time.sleep(0.5)  # be a polite scraper

    for a in all_articles:
        prior = first_seen_published.get(a["link"])
        if prior:
            a["published"] = prior

    # Newest first; entries with no parseable date sink to the bottom.
    all_articles.sort(key=lambda a: a["published"] or "", reverse=True)

    # De-dupe by link in case a story gets syndicated across feeds.
    seen = set()
    deduped = []
    for a in all_articles:
        if a["link"] in seen:
            continue
        seen.add(a["link"])
        deduped.append(a)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "news.json"
    out_path.write_text(__import__("json").dumps(deduped, indent=2, ensure_ascii=False))
    print(f"Wrote {len(deduped)} articles to {out_path}")
    return deduped


if __name__ == "__main__":
    main()
