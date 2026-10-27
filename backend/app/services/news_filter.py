"""Attribution de devises / actifs à une news, par mots-clés (titre + résumé).

Deux sortes de mots-clés par étiquette :
- KEYWORDS : insensibles à la casse ("gold", "bank of japan") ;
- ACRONYMS : sensibles à la casse ("Fed", "BoE", "US") pour éviter les faux positifs ("fed up", "us").
Les noms des gouverneurs changent : mettre ces listes à jour si besoin.
"""

import re
from functools import lru_cache

KEYWORDS: dict[str, list[str]] = {
    "USD": ["federal reserve", "fomc", "powell", "us dollar", "u.s. dollar", "greenback", "dollar index",
            "treasury yields", "treasuries", "nonfarm", "non-farm", "payrolls", "jobless claims", "united states",
            "white house", "u.s.", "us economy", "us inflation", "us cpi", "us jobs", "us gdp", "jolts"],
    "EUR": ["european central bank", "lagarde", "eurozone", "euro zone", "euro area", "euro", "germany", "german",
            "bundesbank", "eurostat", "france", "french", "italy", "italian", "spain", "schnabel"],
    "GBP": ["bank of england", "bailey", "sterling", "pound", "gilts", "gilt", "united kingdom", "britain", "british"],
    "JPY": ["bank of japan", "ueda", "yen", "japan", "japanese", "tankan", "tokyo"],
    "CHF": ["swiss national bank", "swiss franc", "switzerland", "swiss", "schlegel"],
    "AUD": ["reserve bank of australia", "aussie", "australia", "australian", "bullock"],
    "CAD": ["bank of canada", "loonie", "canada", "canadian", "macklem"],
    "NZD": ["reserve bank of new zealand", "kiwi", "new zealand"],
    "SGD": ["monetary authority of singapore", "singapore"],
    "HKD": ["hong kong", "hkma"],
    "NOK": ["norges bank", "norway", "norwegian"],
    "SEK": ["riksbank", "sweden", "swedish", "krona"],
    "DKK": ["danmarks nationalbank", "denmark", "danish"],
    "PLN": ["national bank of poland", "poland", "polish", "zloty"],
    "CZK": ["czech national bank", "czech", "koruna"],
    "HUF": ["national bank of hungary", "hungary", "hungarian", "forint"],
    "TRY": ["central bank of the republic of turkey", "turkey", "turkish", "türkiye", "turkiye", "lira"],
    "ZAR": ["south african reserve bank", "south africa", "south african", "rand"],
    "MXN": ["banxico", "bank of mexico", "mexico", "mexican"],
    "CNH": ["people's bank of china", "china", "chinese", "yuan", "renminbi", "beijing"],
    "THB": ["bank of thailand", "thailand", "thai", "baht"],
    "INR": ["reserve bank of india", "india", "indian", "rupee"],
    "MAD": ["bank al-maghrib", "bank al maghrib", "morocco", "moroccan", "dirham"],
    "XAU": ["gold", "bullion", "precious metals"],
    "XAG": ["silver", "precious metals"],
    "XPT": ["platinum"],
    "XPD": ["palladium"],
    "BTC": ["bitcoin"],
    "ETH": ["ethereum", "ether"],
    "SOL": ["solana"],
    "XRP": ["xrp", "ripple"],
    "BNB": ["bnb chain", "binance coin"],
    "CRYPTO": ["crypto", "cryptocurrency", "cryptocurrencies", "stablecoin", "stablecoins", "blockchain", "binance",
               "coinbase", "altcoin", "altcoins", "defi"],
    "OIL": ["oil", "crude", "opec", "opec+", "brent", "wti", "barrel", "barrels", "petroleum"],
    "NATGAS": ["natural gas", "lng", "henry hub"],
    "US_STOCKS": ["wall street", "s&p 500", "s&p500", "nasdaq", "dow jones", "russell 2000", "us stocks", "u.s. stocks"],
    "DE_STOCKS": ["dax", "frankfurt stocks", "german stocks"],
    "UK_STOCKS": ["ftse", "london stocks"],
    "FR_STOCKS": ["cac 40", "cac40", "paris bourse"],
    "JP_STOCKS": ["nikkei", "topix"],
}

ACRONYMS: dict[str, list[str]] = {
    "USD": ["Fed", "US", "USD", "NFP", "FOMC", "DXY", "PCE", "ISM", "BLS"],
    "EUR": ["EUR", "ECB", "EU", "HICP", "ZEW", "Ifo"],
    "GBP": ["GBP", "BoE", "BOE", "UK", "ONS"],
    "JPY": ["JPY", "BoJ", "BOJ", "JGB", "JGBs"],
    "CHF": ["CHF", "SNB"],
    "AUD": ["AUD", "RBA"],
    "CAD": ["CAD", "BoC", "BOC"],
    "NZD": ["NZD", "RBNZ"],
    "SGD": ["SGD", "MAS"],
    "HKD": ["HKD", "HKMA"],
    "NOK": ["NOK"],
    "SEK": ["SEK"],
    "DKK": ["DKK"],
    "PLN": ["PLN", "NBP"],
    "CZK": ["CZK", "CNB"],
    "HUF": ["HUF", "MNB"],
    "TRY": ["TRY", "CBRT"],
    "ZAR": ["ZAR", "SARB"],
    "MXN": ["MXN"],
    "CNH": ["CNH", "CNY", "PBoC", "PBOC"],
    "THB": ["THB"],
    "INR": ["INR", "RBI"],
    "MAD": ["MAD", "BAM"],
    "XAU": ["XAU"],
    "XAG": ["XAG"],
    "XPT": ["XPT"],
    "XPD": ["XPD"],
    "BTC": ["BTC"],
    "ETH": ["ETH"],
    "SOL": ["SOL"],
    "BNB": ["BNB"],
    "OIL": ["EIA"],
    "US_STOCKS": ["SPX"],
}

CRYPTO_ASSETS = {"BTC", "ETH", "SOL", "XRP", "BNB"}
# Codes reconnus dans les paires écrites "EUR/USD" ou "EURUSD".
PAIR_CODES = {code for code in ACRONYMS if len(code) == 3 and code.isupper()} | {"XAU", "XAG", "XPT", "XPD", "BTC", "ETH"}
_PAIR_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z]{3})/?([A-Z]{3})(?![A-Za-z0-9])")


def _alternation(terms: list[str]) -> str:
    return "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True))


@lru_cache
def _patterns() -> dict[str, list[re.Pattern[str]]]:
    boundary = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"
    patterns: dict[str, list[re.Pattern[str]]] = {}
    for tag in set(KEYWORDS) | set(ACRONYMS):
        compiled = []
        if KEYWORDS.get(tag):
            compiled.append(re.compile(boundary.format(f"(?:{_alternation(KEYWORDS[tag])})"), re.IGNORECASE))
        if ACRONYMS.get(tag):
            compiled.append(re.compile(boundary.format(f"(?:{_alternation(ACRONYMS[tag])})")))
        patterns[tag] = compiled
    return patterns


def detect_tags(text: str) -> set[str]:
    tags = {tag for tag, patterns in _patterns().items() if any(pattern.search(text) for pattern in patterns)}
    for first, second in _PAIR_RE.findall(text):
        if first in PAIR_CODES and second in PAIR_CODES:
            tags.update((first, second))
    if tags & CRYPTO_ASSETS:
        tags.add("CRYPTO")
    return tags


def tag_news(title: str, summary: str | None = None, default_tags: list[str] | None = None) -> list[str]:
    """Étiquettes d'une news : celles imposées par la source + celles détectées dans le texte."""
    tags = set(default_tags or [])
    tags |= detect_tags(f"{title}\n{summary or ''}")
    return sorted(tags)
