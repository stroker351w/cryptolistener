"""Shared helpers: lightweight RSS/Atom parsing (no feedparser dependency,
since it drags in an unmaintained sgmllib3k dep that fails to build on
recent Python) and small IO helpers used by the other scripts.
"""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from dateutil import parser as dateparser

USER_AGENT = "Mozilla/5.0 (compatible; cryptolistener/1.0; +https://github.com/stroker351w/cryptolistener)"

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def strip_html(text: str) -> str:
    """Remove tags and unescape entities so summaries render as plain text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value: str):
    """Return a timezone-aware UTC datetime, or None if unparsable."""
    if not value:
        return None
    for fn in (parsedate_to_datetime, dateparser.parse):
        try:
            dt = fn(value)
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def parse_feed(xml_text: str):
    """Parse an RSS 2.0 or Atom feed into a list of
    {title, link, summary, published} dicts. Best-effort: skips entries
    it can't make sense of rather than raising.
    """
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    # RSS 2.0 / RDF: <item> elements anywhere in the tree
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        summary = item.findtext("description") or item.findtext(
            "{http://purl.org/rss/1.0/modules/content/}encoded"
        ) or ""
        published = (
            item.findtext("pubDate")
            or item.findtext("{http://purl.org/dc/elements/1.1/}date")
            or ""
        )
        if title and link:
            items.append(
                {
                    "title": html.unescape(title).strip(),
                    "link": link,
                    "summary": strip_html(summary)[:400],
                    "published": published,
                }
            )

    if items:
        return items

    # Atom: <entry> elements
    for entry in root.iter(f"{ATOM_NS}entry"):
        title = (entry.findtext(f"{ATOM_NS}title") or "").strip()
        link = ""
        for link_el in entry.findall(f"{ATOM_NS}link"):
            rel = link_el.get("rel", "alternate")
            if rel == "alternate" or not link:
                link = link_el.get("href", link)
        summary = entry.findtext(f"{ATOM_NS}summary") or entry.findtext(
            f"{ATOM_NS}content"
        ) or ""
        published = (
            entry.findtext(f"{ATOM_NS}published")
            or entry.findtext(f"{ATOM_NS}updated")
            or ""
        )
        if title and link:
            items.append(
                {
                    "title": html.unescape(title).strip(),
                    "link": link,
                    "summary": strip_html(summary)[:400],
                    "published": published,
                }
            )
    return items


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
