"""Heuristic "worth a second look" flag.

Be clear-eyed about what this is: a case-insensitive keyword match against
each article's title + summary. It is NOT sentiment analysis, NOT an LLM
judging actual impact, and it doesn't know direction (good news and bad
news both get flagged). It will produce both false positives (a keyword
appears in an unrelated context) and false negatives (a real story that
happens to avoid these exact words). Treat the flag as "worth a second
look", not as verified impact.

Two-gate design (both must match): a bare "SEC" or "ETF" keyword alone is
nearly meaningless once the SEC's own press-release feed is in the mix --
most of what the SEC does has nothing to do with crypto. So a story only
flags if it mentions BOTH something crypto-specific AND something in the
impact bucket (regulation, custody, ETFs, institutional adoption).

Edit CRYPTO_TERMS / IMPACT_TERMS directly to tune this -- flat lists on
purpose so they're easy to scan and adjust without touching the logic.
"""
import re

# Gate 1: the story has to actually be about crypto/digital assets.
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

# Gate 2: something that plausibly matters beyond the headline -- the ETF
# complex, the regulation that shapes what custodians/issuers can offer,
# or institutional demand for custody/trading services.
IMPACT_TERMS = [
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
_IMPACT_PATTERN = re.compile("|".join(IMPACT_TERMS), re.IGNORECASE)


def is_relevant(title: str, summary: str = "") -> bool:
    text = f"{title} {summary}"
    return bool(_CRYPTO_PATTERN.search(text)) and bool(_IMPACT_PATTERN.search(text))
