#!/usr/bin/env python3
"""Best-effort fetch of crypto-related X (Twitter) posts.

Reality check (tested live on 2026-09-03, see README for detail):
  - X killed the free API tier in Feb 2026; a usable read tier costs money.
  - Every public Nitter-style mirror is dead, 410-gone, connection-refused,
    rate-limited, or sitting behind a JS/CAPTCHA anti-bot wall. None of them
    return real data unauthenticated right now.
  - The only unofficial route with any real chance of working is replaying
    a *logged-in* X session's own cookies against X's internal GraphQL API
    (the same technique tools like twscrape use). That's what this script
    does, IF you configure it -- see README "Optional: X integration".

This is opt-in and degrades gracefully: with no credentials configured it
writes an empty result and the site just omits the X section, instead of
breaking the whole pipeline.

Maintenance note: X rotates the GraphQL `queryId` for SearchTimeline
periodically. If this starts failing, open twitter.com/x.com in a browser,
do a search, find the `SearchTimeline` request in devtools' Network tab,
and copy the queryId + any changed field names into SEARCH_QUERY_ID below.
This was NOT validated against a live authenticated session while building
it (no test account available) -- treat it as a documented starting point.
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

# Public bearer token embedded in X's own web client JS bundle -- not a
# secret, just an identifier every browser session uses. Pairs with your
# account cookies below to authenticate as *you*.
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
SEARCH_QUERY_ID = "gkjsKepM6gl_HmFWoWKfgg"  # SearchTimeline -- rotates; see docstring
SEARCH_URL = f"https://x.com/i/api/graphql/{SEARCH_QUERY_ID}/SearchTimeline"

KEYWORDS = ["bitcoin", "ethereum", "crypto", "defi", "solana"]
MAX_POSTS_PER_KEYWORD = 10


def get_credentials():
    auth_token = os.environ.get("X_AUTH_TOKEN")
    ct0 = os.environ.get("X_CT0")
    if not auth_token or not ct0:
        return None
    return auth_token, ct0


def build_session(auth_token: str, ct0: str) -> requests.Session:
    s = requests.Session()
    s.cookies.set("auth_token", auth_token, domain=".x.com")
    s.cookies.set("ct0", ct0, domain=".x.com")
    s.headers.update(
        {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "x-csrf-token": ct0,
            "User-Agent": "Mozilla/5.0 (compatible; cryptolistener/1.0)",
            "Content-Type": "application/json",
        }
    )
    return s


def search_keyword(session: requests.Session, keyword: str):
    variables = {
        "rawQuery": keyword,
        "count": MAX_POSTS_PER_KEYWORD,
        "querySource": "typed_query",
        "product": "Top",
    }
    features = {
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "tweetypie_unmention_optimization_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_media_download_video_enabled": False,
        "responsive_web_enhance_cards_enabled": False,
    }
    params = {"variables": json.dumps(variables), "features": json.dumps(features)}
    resp = session.get(SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def extract_posts(raw: dict, keyword: str):
    """Walk the GraphQL response tree defensively -- its shape has changed
    before and will change again."""
    posts = []
    try:
        instructions = raw["data"]["search_by_raw_query"]["search_timeline"][
            "timeline"
        ]["instructions"]
    except (KeyError, TypeError):
        return posts

    for instruction in instructions:
        for entry in instruction.get("entries", []):
            try:
                tweet = entry["content"]["itemContent"]["tweet_results"]["result"]
                legacy = tweet.get("legacy", {})
                user = tweet["core"]["user_results"]["result"]["legacy"]
                posts.append(
                    {
                        "keyword": keyword,
                        "author": user.get("screen_name"),
                        "text": legacy.get("full_text", "")[:400],
                        "created_at": legacy.get("created_at"),
                        "likes": legacy.get("favorite_count", 0),
                        "retweets": legacy.get("retweet_count", 0),
                        "url": f"https://x.com/{user.get('screen_name')}/status/{tweet.get('rest_id')}",
                    }
                )
            except (KeyError, TypeError):
                continue
    return posts


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "x_posts.json"

    creds = get_credentials()
    if not creds:
        print(
            "X_AUTH_TOKEN/X_CT0 not configured -- skipping X entirely "
            "(see README for optional setup). This is expected and not an error."
        )
        out_path.write_text(json.dumps({"enabled": False, "posts": []}, indent=2))
        return

    session = build_session(*creds)
    all_posts = []
    for keyword in KEYWORDS:
        try:
            raw = search_keyword(session, keyword)
            posts = extract_posts(raw, keyword)
            print(f"  [ok]   '{keyword}': {len(posts)} posts")
            all_posts.extend(posts)
        except requests.RequestException as exc:
            print(f"  [skip] '{keyword}': request failed: {exc}", file=sys.stderr)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            print(
                f"  [skip] '{keyword}': response shape didn't match what this "
                f"script expects ({exc}). X likely changed their API again -- "
                f"see the maintenance note at the top of this file.",
                file=sys.stderr,
            )

    # Rank by a crude engagement score as a stand-in for "trending"
    all_posts.sort(key=lambda p: p["likes"] + p["retweets"] * 2, reverse=True)

    # De-dupe by URL (same post can surface under multiple keywords)
    seen = set()
    deduped = []
    for p in all_posts:
        if p["url"] in seen:
            continue
        seen.add(p["url"])
        deduped.append(p)

    out_path.write_text(json.dumps({"enabled": True, "posts": deduped[:30]}, indent=2))
    print(f"Wrote {len(deduped[:30])} X posts to {out_path}")


if __name__ == "__main__":
    main()
