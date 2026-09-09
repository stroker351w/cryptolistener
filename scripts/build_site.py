#!/usr/bin/env python3
"""Render data/news.json + data/x_posts.json into docs/index.html
(the file GitHub Pages serves)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
from utils import load_json  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def humanize(iso_str):
    if not iso_str:
        return "date unknown"
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return "date unknown"
    delta = datetime.now(timezone.utc) - dt
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f"{int(delta.total_seconds() / 60)}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours / 24)}d ago"


def format_price(p):
    if p is None:
        return "—"
    if p >= 1000:
        return f"${p:,.0f}"
    if p >= 1:
        return f"${p:,.2f}"
    if p >= 0.01:
        return f"${p:.4f}"
    return f"${p:.6f}"


def main():
    articles = load_json(DATA_DIR / "news.json", [])
    for a in articles:
        a["published_display"] = humanize(a.get("published"))
        a.setdefault("category", "event")  # stale data.json from before the split
        # stale data.json from before the flag split, or from the old combined "relevant" flag
        a.setdefault("regulatory", a.get("relevant", False))
        a.setdefault("institutional", False)

    event_articles = [a for a in articles if a["category"] != "sentiment"]
    sentiment_articles = [a for a in articles if a["category"] == "sentiment"]
    sources = sorted({a["source"] for a in articles if a.get("source")})

    x_data = load_json(DATA_DIR / "x_posts.json", {"enabled": False, "posts": []})

    price_data = load_json(DATA_DIR / "prices.json", {"fetched_at": None, "coins": []})
    if isinstance(price_data, list):
        # Old format (before prices.json started recording fetched_at):
        # a bare list of coins with no fetch timestamp.
        price_data = {"fetched_at": None, "coins": price_data}
    prices = price_data.get("coins", [])
    for p in prices:
        p["price_display"] = format_price(p.get("price"))
        p["change_display"] = (
            f"{p['change_24h']:+.1f}%" if p.get("change_24h") is not None else "—"
        )
        p["change_up"] = (p.get("change_24h") or 0) >= 0
    fetched_at = price_data.get("fetched_at")
    prices_age_display = humanize(fetched_at) if fetched_at else None

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html.j2")
    html = template.render(
        articles=articles,
        event_articles=event_articles,
        sentiment_articles=sentiment_articles,
        sources=sources,
        x_enabled=x_data.get("enabled", False),
        x_posts=x_data.get("posts", []),
        prices=prices,
        prices_age_display=prices_age_display,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "index.html"
    out_path.write_text(html)
    print(f"Wrote {out_path} ({len(articles)} articles, x_enabled={x_data.get('enabled', False)})")


if __name__ == "__main__":
    main()
