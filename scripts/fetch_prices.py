#!/usr/bin/env python3
"""Pull the top 10 cryptocurrencies by market cap for the header ticker.

Uses CoinGecko's free public /coins/markets endpoint -- no API key, no
cost. It's rate-limited per IP (roughly 10-30 calls/min), which is a
non-issue here since this runs once per scheduled build (hourly), not
per site visitor. If CoinGecko is unreachable or rate-limits us, this
degrades gracefully: the ticker just keeps showing the last successful
fetch (data/prices.json isn't overwritten) instead of breaking the build.

Stablecoins and a small manual exclude-list are filtered out before
picking the top 10, since "top 10 crypto by market cap" is meant to
show volatile, price-discovering assets, not dollar-pegged tokens or
non-market instruments that happen to have a market-cap-shaped number:

- Stablecoins (USDT, USDC, DAI, etc.) are identified via CoinGecko's
  own `category=stablecoins` listing, fetched fresh on every run so we
  don't have to hand-maintain the list as new stablecoins launch.
- MANUAL_EXCLUDE_IDS covers assets that aren't stablecoins but also
  aren't really "crypto prices" in the sense this ticker means.
  figure-heloc (FIGR_HELOC) is a tokenized representation of HELOC
  loan balances on the Provenance blockchain (Figure Technologies) --
  its "price" tracks a loan balance, not market trading, so including
  it in a top-10-by-market-cap ticker is misleading. Add more ids here
  if similar tokenized-RWA/loan-balance assets show up in the top 50.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from utils import USER_AGENT, save_json  # noqa: E402

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "prices.json"

MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
# Pull a larger candidate pool than we need (10) so that filtering out
# stablecoins/exclusions still leaves enough coins to fill the top 10.
CANDIDATE_PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 50,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "24h",
}
STABLECOIN_PARAMS = {
    "vs_currency": "usd",
    "category": "stablecoins",
    "order": "market_cap_desc",
    "per_page": 250,
    "page": 1,
}
REQUEST_TIMEOUT = 15
TARGET_COUNT = 10

MANUAL_EXCLUDE_IDS = {
    # Tokenized HELOC loan-balance data (Figure Technologies / Provenance
    # blockchain), not a traded speculative asset -- see module docstring.
    "figure-heloc",
}


def fetch_json(url, params):
    resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def main():
    try:
        candidates = fetch_json(MARKETS_URL, CANDIDATE_PARAMS)
    except (requests.RequestException, ValueError) as exc:
        print(f"  [skip] CoinGecko prices: {exc} -- leaving previous data/prices.json in place", file=sys.stderr)
        return

    try:
        stablecoins = fetch_json(MARKETS_URL, STABLECOIN_PARAMS)
        stablecoin_ids = {c.get("id") for c in stablecoins}
    except (requests.RequestException, ValueError) as exc:
        # Don't fail the whole ticker just because the stablecoin lookup
        # failed -- fall back to the manual list only, and say so.
        print(f"  [warn] CoinGecko stablecoin lookup failed: {exc} -- filtering with manual exclude list only", file=sys.stderr)
        stablecoin_ids = set()

    exclude_ids = stablecoin_ids | MANUAL_EXCLUDE_IDS

    coins = []
    for c in candidates:
        if c.get("id") in exclude_ids:
            continue
        coins.append(
            {
                "symbol": (c.get("symbol") or "").upper(),
                "name": c.get("name"),
                "price": c.get("current_price"),
                "change_24h": c.get("price_change_percentage_24h"),
            }
        )
        if len(coins) == TARGET_COUNT:
            break

    if not coins:
        print("  [skip] CoinGecko prices: empty response -- leaving previous data/prices.json in place", file=sys.stderr)
        return

    # Re-rank sequentially 1-N for display, since excluded coins would
    # otherwise leave gaps in CoinGecko's raw market_cap_rank (e.g. "#3,
    # #4, #7..." if #5 and #6 were stablecoins).
    for i, coin in enumerate(coins, start=1):
        coin["market_cap_rank"] = i

    save_json(OUT_PATH, coins)
    print(f"Wrote {len(coins)} prices to {OUT_PATH} (excluded {len(exclude_ids)} stablecoin/manual ids from candidate pool)")


if __name__ == "__main__":
    main()
