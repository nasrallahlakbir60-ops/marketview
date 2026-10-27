"""Tables initiales : pairs, news, news_currencies, macro_indicators, economic_events

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pairs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("base_currency", sa.String(10), nullable=False),
        sa.Column("quote_currency", sa.String(10), nullable=False),
        sa.Column("tradingview_symbol", sa.String(60), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_pairs_symbol", "pairs", ["symbol"], unique=True)
    op.create_index("ix_pairs_category", "pairs", ["category"])

    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentiment", sa.String(16), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_news_published_at", "news", ["published_at"])
    op.create_index("ix_news_hash", "news", ["hash"], unique=True)

    op.create_table(
        "news_currencies",
        sa.Column("news_id", sa.Integer(), sa.ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("currency", sa.String(12), primary_key=True),
    )
    op.create_index("ix_news_currencies_currency", "news_currencies", ["currency"])

    op.create_table(
        "macro_indicators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("indicator", sa.String(32), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("previous", sa.Float(), nullable=True),
        sa.Column("forecast", sa.Float(), nullable=True),
        sa.Column("period", sa.String(16), nullable=True),
        sa.Column("previous_period", sa.String(16), nullable=True),
        sa.Column("frequency", sa.String(16), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("country", "indicator", "source", name="uq_macro_country_indicator_source"),
    )
    op.create_index("ix_macro_indicators_country", "macro_indicators", ["country"])

    op.create_table(
        "economic_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("event_name", sa.String(200), nullable=False),
        sa.Column("impact", sa.String(10), nullable=False),
        sa.Column("actual", sa.Float(), nullable=True),
        sa.Column("forecast", sa.Float(), nullable=True),
        sa.Column("previous", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(16), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.UniqueConstraint("country", "event_name", "event_time", name="uq_event_country_name_time"),
    )
    op.create_index("ix_economic_events_currency", "economic_events", ["currency"])
    op.create_index("ix_economic_events_event_time", "economic_events", ["event_time"])


def downgrade() -> None:
    op.drop_table("economic_events")
    op.drop_table("macro_indicators")
    op.drop_table("news_currencies")
    op.drop_table("news")
    op.drop_table("pairs")
