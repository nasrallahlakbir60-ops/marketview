from pydantic import BaseModel

from app.models import Pair
from app.services import pair_mapping


class PairOut(BaseModel):
    symbol: str
    name: str
    category: str
    base: str
    quote: str
    tradingview_symbol: str
    active: bool

    @classmethod
    def from_model(cls, pair: Pair) -> "PairOut":
        return cls(
            symbol=pair.symbol,
            name=pair.name,
            category=pair.category,
            base=pair.base_currency,
            quote=pair.quote_currency,
            tradingview_symbol=pair.tradingview_symbol,
            active=pair.active,
        )


class NewsTag(BaseModel):
    code: str
    label: str


class CountryOut(BaseModel):
    code: str
    name: str
    currency: str


class PairDetail(PairOut):
    news_tags: list[NewsTag]
    macro_countries: list[CountryOut]

    @classmethod
    def from_model(cls, pair: Pair) -> "PairDetail":
        base = PairOut.from_model(pair)
        tags = pair_mapping.news_tags(pair.base_currency, pair.quote_currency, pair.category)
        countries = [
            pair_mapping.country_info(code)
            for code in pair_mapping.macro_countries(pair.base_currency, pair.quote_currency, pair.category)
        ]
        return cls(
            **base.model_dump(),
            news_tags=[NewsTag(code=tag, label=pair_mapping.tag_label(tag)) for tag in tags],
            macro_countries=[CountryOut(code=c.code, name=c.name, currency=c.currency) for c in countries if c],
        )
