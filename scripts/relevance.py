"""Heuristic "worth a second look" flags.

Be clear-eyed about what this is: a case-insensitive keyword match against
each article's title + summary. It is NOT sentiment analysis, NOT an LLM
judging actual impact, and it doesn't know direction (good news and bad
news both get flagged). It will produce both false positives (a keyword
appears in an unrelated context) and false negatives (a real story that
happens to avoid these exact words). Treat these flags as "worth a second
look", not as verified impact.

Two separate flags, not one:

- Regulatory/legal (is_regulatory): SEC/CFTC action, court rulings,
  legislation, custody rules, security-classification fights -- things
  that change what's legally allowed.
- Institutional (is_institutional): adoption/demand signals from asset
  managers, corporate treasuries, and retirement/pension money -- BlackRock
  buying, a company adding BTC to its balance sheet, a 401(k) provider
  adding crypto exposure.

These used to be one combined "relevant" flag, which conflated "the SEC
sued someone" with "BlackRock's ETF saw inflows" -- two very different
kinds of story that happened to share a bucket. Splitting them makes each
flag mean one specific thing.

Two-gate design for each (both must match): a bare "SEC" or "ETF" keyword
alone is nearly meaningless once the SEC's own press-release feed is in
the mix -- most of what the SEC does has nothing to do with crypto. So a
story only flags if it mentions BOTH something crypto-specific AND
something in that flag's own impact bucket.

Edit CRYPTO_TERMS / REGULATORY_TERMS / INSTITUTIONAL_TERMS directly to
tune this -- flat lists on purpose so they're easy to scan and adjust
without touching the logic.
"""
import re

# Gate 1 (shared): the story has to actually be about crypto/digital assets.
CRYPTO_TERMS = [
    r"\bbitcoin\b",
    r"\bcrypto\w*\b",
    "digital asset",
    r"\bblockchain\b",
    r"\bether(eum)?\b",
    r"\btoken\b",
    "stablecoin",
    r"\bdefi\b",
    r"\bweb3\b",
    r"\bibit\b",
    "grayscale",
    "microstrategy",
    "strategy incorporated",
    # Ticker symbols -- unambiguous in this feed's domain (crypto news +
    # SEC releases), so safe to match on their own without the word
    # "crypto" also appearing (e.g. "BitMine Adds 53,501 ETH").
    r"\bbtc\b",
    r"\beth\b",
    r"\bxrp\b",
    r"\bsol\b",
    r"\bada\b",
    r"\bdoge\b",
    r"\bbnb\b",
]

# Gate 2a: law/regulation -- action or rules that change what's legally
# allowed, not just who's buying.
REGULATORY_TERMS = [
    r"\bsec\b",
    r"\bcftc\b",
    "custody",
    "qualified custodian",
    r"\betfs?\b",
    "in-kind redemption",
    "market structure",
    "clarity act",
    "genius act",
    "stablecoin bill",
    "stablecoin legislation",
    "howey test",
    "security classification",
    r"\blawsuit\b",
    r"\bcourt\b",
    r"\bruling\b",
    r"\blegislat\w*\b",
]

# Gate 2b: institutional adoption/demand -- asset managers, corporate
# treasuries, and retirement money moving into crypto.
INSTITUTIONAL_TERMS = [
    "staking",
    "institutional adoption",
    "institutional investor",
    "corporate treasury",
    "401(k)",
    "retirement account",
    "pension fund",
    "blackrock",
    "ark invest",
    "21shares",
    "bitwise",
    "vaneck",
]

_CRYPTO_PATTERN = re.compile("|".join(CRYPTO_TERMS), re.IGNORECASE)
_REGULATORY_PATTERN = re.compile("|".join(REGULATORY_TERMS), re.IGNORECASE)
_INSTITUTIONAL_PATTERN = re.compile("|".join(INSTITUTIONAL_TERMS), re.IGNORECASE)


def is_regulatory(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}"
    return bool(_CRYPTO_PATTERN.search(text)) and bool(_REGULATORY_PATTERN.search(text))


def is_institutional(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}"
    return bool(_CRYPTO_PATTERN.search(text)) and bool(_INSTITUTIONAL_PATTERN.search(text))
