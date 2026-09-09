#!/usr/bin/env python3
"""Pull the top 10 cryptocurrencies by market cap for the header ticker.

Uses CoinGecko's free public /coins/markets endpoint -- no API key, no
cost. It's rate-limited per IP (roughly 10-30 calls/min), which is a
non-issue here since this runs once per scheduled build (hourly), not
per site visitor. If CoinGecko is unreachable or rate-limits us, this
degrades gracefully: the ticker just keeps showing the last successful
fetch (data/prices.json isn't overwritten) instead of breaking the build.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import USER_AGENT, save_json  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "prices.json"

API_URL = "https://api.coingecko.com/api/v3/coins/markets"
PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 10,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "24h",
}
REQUEST_TIMEOUT = 15


def main():
    try:
        resp = requests.get(
            API_URL, params=PARAMS, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        raw = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"  [skip] CoinGecko prices: {exc} -- leaving previous data/prices.json in place", file=sys.stderr)
        return

    coins = []
    for c in raw:
        coins.append(
            {
                "symbol": (c.get("symbol") or "").upper(),
                "name": c.get("name"),
                "price": c.get("current_price"),
                "change_24h": c.get("price_change_percentage_24h"),
                "market_cap_rank": c.get("market_cap_rank"),
            }
        )

    if not coins:
        print("  [skip] CoinGecko prices: empty response -- leaving previous data/prices.json in place", file=sys.stderr)
        return

    save_json(OUT_PATH, coins)
    print(f"Wrote {len(coins)} prices to {OUT_PATH}")


if __name__ == "__main__":
    main()
