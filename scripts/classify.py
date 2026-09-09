"""Split articles into two buckets for the site's two-column layout.

"event"     -- hard news: launches, filings, lawsuits, hacks, partnerships,
               rulings, listings, acquisitions, product releases, etc.
"sentiment" -- market commentary: price predictions, bullish/bearish takes,
               "here's why" analysis, outlooks/forecasts, opinion pieces.

Same spirit as relevance.py: a plain keyword heuristic, not real
classification. It will misfile some articles either direction -- a
headline like "Bitcoin ETF Approved After Weeks of Speculation" is a hard
event even though it contains "speculation". Treat the split as a rough
sort, not a guarantee. "event" is the default bucket; an article only
lands in "sentiment" if it trips one of the patterns below. Tune
SENTIMENT_TERMS directly if a category feels wrong often enough to matter.
"""
import re

SENTIMENT_TERMS = [
    # Hedged "why it could/might happen" framing -- specific enough to be a
    # reliable signal (unlike bare "could"/"might"/"may", which show up
    # constantly in ordinary hard-news summaries and were dropped after
    # testing showed they misfired on things like acquisition writeups).
    "here's why", "here is why", r"\bwhy \w+ (is|are|could|might)\b",
    "opinion:", "analysis:", "price analysis", "technical analysis",
    r"\boutlook\b", r"\bforecast(s|ed|ing)?\b",
    # Negative lookahead excludes "prediction market(s)" -- that's a
    # product/business category (see Polymarket, Robinhood's push into
    # them), not a forecast about price.
    r"\bpredictions?\b(?![\s-]+market)", r"\bpredicts?\b",
    "price target", r"\btarget of\b",
    # Market mood / commentary words.
    r"\bbullish\b", r"\bbearish\b", r"\bsentiment\b",
    r"\brally(ing)?\b", r"\bsurge[sd]?\b", r"\bsoar(s|ed|ing)?\b",
    r"\bplunge[sd]?\b", r"\btank(s|ed|ing)?\b", r"\bdip\b",
    r"analysts?\s+(say|says|said|expect|expects|predict|predicts|believe|believes)",
    r"traders?\s+(bet|bets|expect|are watching|are betting)",
    # Retail-facing "should I buy" framing.
    "should you buy", "best crypto to buy", "top picks",
    "buy the dip", "is it too late", "is now the time",
]

_SENTIMENT_PATTERN = re.compile("|".join(SENTIMENT_TERMS), re.IGNORECASE)

# A question-mark headline about the market is very often commentary
# ("Is Bitcoin Ready to Rally?") rather than a reported event.
_MARKET_TOPIC = re.compile(
    r"\b(bitcoin|crypto\w*|ethereum|eth|btc|xrp|sol|market|price)\b",
    re.IGNORECASE,
)


def classify(title: str, summary: str = "") -> str:
    """Return "sentiment" or "event"."""
    if title.rstrip().endswith("?") and _MARKET_TOPIC.search(title):
        return "sentiment"
    text = f"{title} {summary}"
    if _SENTIMENT_PATTERN.search(text):
        return "sentiment"
    return "event"
