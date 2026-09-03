# cryptolistener

A self-updating crypto news aggregator. A scheduled GitHub Action pulls
articles from 11 crypto news RSS feeds every hour, optionally pulls
crypto-related X (Twitter) posts, and rebuilds a static page published via
GitHub Pages.

**Live site:** enable Pages once (see below), then it's
`https://stroker351w.github.io/cryptolistener/`.

## How it works

```
scripts/fetch_rss.py   -> data/news.json      (11 RSS feeds, deduped, sorted newest-first)
scripts/fetch_x.py     -> data/x_posts.json   (optional, see below)
scripts/build_site.py  -> docs/index.html     (what GitHub Pages serves)
```

`.github/workflows/update.yml` runs all three every hour (`workflow_dispatch`
also lets you trigger a run manually from the Actions tab) and commits the
result back to `main` if anything changed.

### News sources

CoinDesk, Cointelegraph, Decrypt, The Block, Bitcoin Magazine, CryptoSlate,
The Defiant, Blockworks, U.Today, NewsBTC, CryptoPotato. All verified live
as of 2026-09-03. If one of these goes offline or changes its feed URL,
`fetch_rss.py` just logs a skip for that source and keeps going — edit the
`SOURCES` dict in that file to fix the URL or drop it.

## One-time setup

1. **Enable GitHub Pages**: Settings → Pages → Source: "Deploy from a
   branch" → Branch: `main`, folder: `/docs` → Save.
   (I tried to do this for you via the API when I first pushed; if it
   didn't take, this is the manual fallback — takes about 30 seconds.)
2. That's it for the news side. It'll start updating hourly on its own.

## Optional: X (Twitter) integration

Read this before turning it on.

**Why it's opt-in and off by default:** X shut off its free API tier in
February 2026, and there's no official affordable way to read search
results or trending topics anymore (paid pay-per-use, or a $42k/month
Enterprise contract for anything more). Every public unofficial workaround
(Nitter and its mirrors) is now dead, rate-limited, or behind a
JS/CAPTCHA wall — I tested seven of them live while building this and none
returned real data anonymously.

**What this actually does instead:** `scripts/fetch_x.py` replays your own
logged-in X session's cookies against X's internal (undocumented) GraphQL
API — the same technique tools like `twscrape` use. It is *not* endorsed
by X, it's a gray area under their Terms of Service, and using it puts
your account at some risk of action from X (rate limiting, a challenge, or
in the worst case a suspension) if it's flagged as automated. Don't enable
it on an account you can't afford to have that happen to — consider a
throwaway/secondary account instead of your main one.

**This code path was not tested against a live account** while building it
(I had no test account to verify with) — treat it as a documented starting
point, not a guarantee. X also rotates the internal GraphQL `queryId` it
uses periodically; if it stops working, the fix is described in the
comment at the top of `fetch_x.py`.

To enable it:

1. Log into x.com in your browser normally.
2. Open devtools → Application/Storage → Cookies → x.com, and copy the
   values of the `auth_token` and `ct0` cookies.
3. In this repo: Settings → Secrets and variables → Actions → New
   repository secret. Add `X_AUTH_TOKEN` (the `auth_token` value) and
   `X_CT0` (the `ct0` value).
4. Next scheduled run (or trigger one manually from the Actions tab) will
   pick them up automatically. If it's misconfigured or X has changed
   something, the site just shows "X integration configured but returned
   no posts" instead of failing the whole pipeline — check the Action's
   log for the actual error.

These cookies expire periodically (logging out anywhere invalidates them,
and X also rotates them on its own on a schedule) — if X posts stop
showing up after a while, that's the most likely reason; repeat the steps
above to refresh them.

## Local development

```
pip install -r requirements.txt
python scripts/fetch_rss.py
python scripts/fetch_x.py      # no-op unless X_AUTH_TOKEN/X_CT0 are set
python scripts/build_site.py
open docs/index.html
```

## Known limitations

- RSS summaries are whatever each publisher puts in their feed — some are
  full articles, some are one-line teasers.
- "Trending" for X posts is a crude engagement score (likes + 2×retweets)
  across a handful of hardcoded keywords, not X's real trending algorithm.
- This is display-only — there's no dedup against previously-seen articles
  across runs beyond what's in the current `data/news.json` snapshot, so
  an article that later gets removed from a source's feed will drop off
  the page rather than being archived.
