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


def main():
    articles = load_json(DATA_DIR / "news.json", [])
    for a in articles:
        a["published_display"] = humanize(a.get("published"))

    x_data = load_json(DATA_DIR / "x_posts.json", {"enabled": False, "posts": []})

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("index.html.j2")
    html = template.render(
        articles=articles,
        x_enabled=x_data.get("enabled", False),
        x_posts=x_data.get("posts", []),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_DIR / "index.html"
    out_path.write_text(html)
    print(f"Wrote {out_path} ({len(articles)} articles, x_enabled={x_data.get('enabled', False)})")


if __name__ == "__main__":
    main()
