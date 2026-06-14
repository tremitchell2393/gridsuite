"""initial schema

Creates all core tables: organizations, users, subscriptions, signals,
forecasts, watched_lanes, alert_rules, ecosystem data tables.

Also converts `signals` and `forecasts` to TimescaleDB hypertables,
partitioned on their time columns — per architecture doc section 3
("In production this table should be converted to a TimescaleDB
hypertable"). The hypertable conversion is wrapped in a try/except via
raw SQL with `IF NOT EXISTS`-style guards where possible; if running
against a Postgres instance WITHOUT the Timescale extension (e.g. local
dev), set `ENABLE_TIMESCALE=false` as an env var before running this
migration and the hypertable calls will be skipped.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-01-01
"""
import os

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

ENABLE_TIMESCALE = os.environ.get("ENABLE_TIMESCALE", "true").lower() == "true"


def upgrade() -> None:
    # ── Organizations / Users / Subscriptions ──
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("is_org_admin", sa.Boolean(), server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    subscription_tier_enum = postgresql.ENUM(
        "core", "pro", "enterprise", "institutional", name="subscriptiontier"
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
        sa.Column("tier", subscription_tier_enum, nullable=False, server_default="core"),
        sa.Column("stripe_subscription_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("lane_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # ── Signal Store ──
    op.create_table(
        "signals",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("signal_id", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_signals_signal_id", "signals", ["signal_id"])
    op.create_index("ix_signals_entity_type", "signals", ["entity_type"])
    op.create_index("ix_signals_entity_id", "signals", ["entity_id"])
    op.create_index("ix_signals_timestamp", "signals", ["timestamp"])
    op.create_index("ix_signals_lookup", "signals", ["signal_id", "entity_type", "entity_id", "timestamp"])

    # ── Forecasts ──
    op.create_table(
        "forecasts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("forecast_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("lower_bound", sa.Float(), nullable=True),
        sa.Column("upper_bound", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("signal_attribution", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("realized_value", sa.Float(), nullable=True),
    )
    op.create_index("ix_forecasts_forecast_type", "forecasts", ["forecast_type"])
    op.create_index("ix_forecasts_entity_type", "forecasts", ["entity_type"])
    op.create_index("ix_forecasts_entity_id", "forecasts", ["entity_id"])
    op.create_index("ix_forecasts_generated_at", "forecasts", ["generated_at"])
    op.create_index("ix_forecasts_target_date", "forecasts", ["target_date"])
    op.create_index("ix_forecasts_lookup", "forecasts", ["forecast_type", "entity_type", "entity_id", "target_date"])

    # ── Watched Lanes ──
    op.create_table(
        "watched_lanes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lane_id", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_watched_lanes_org", "watched_lanes", ["organization_id"])

    # ── Alert Rules ──
    alert_channel_enum = postgresql.ENUM("email", "slack", "webhook", name="alertchannel")
    alert_condition_enum = postgresql.ENUM(
        "forecast_change_above", "signal_threshold", "confidence_above", name="alertcondition"
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("lane_id", sa.String(50), nullable=False),
        sa.Column("signal_or_forecast_type", sa.String(100), nullable=False),
        sa.Column("condition", alert_condition_enum, nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("channel", alert_channel_enum, nullable=False),
        sa.Column("destination", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alert_rules_org", "alert_rules", ["organization_id"])

    # ── Ecosystem Data ──
    op.create_table(
        "ecosystem_data_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("lane_id", sa.String(50), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ecosystem_submissions_org", "ecosystem_data_submissions", ["organization_id"])

    op.create_table(
        "ecosystem_benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("lane_id", sa.String(50), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("median_value", sa.Float(), nullable=False),
        sa.Column("p25_value", sa.Float(), nullable=False),
        sa.Column("p75_value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("contributor_count", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ecosystem_benchmarks_data_type", "ecosystem_benchmarks", ["data_type"])
    op.create_index("ix_ecosystem_benchmarks_lane_id", "ecosystem_benchmarks", ["lane_id"])

    # ── TimescaleDB hypertable conversion ──
    # Skipped automatically if ENABLE_TIMESCALE=false (e.g. local dev
    # against plain Postgres without the Timescale extension).
    if ENABLE_TIMESCALE:
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb;")
        op.execute(
            "SELECT create_hypertable('signals', 'timestamp', "
            "if_not_exists => TRUE, migrate_data => TRUE);"
        )
        op.execute(
            "SELECT create_hypertable('forecasts', 'generated_at', "
            "if_not_exists => TRUE, migrate_data => TRUE);"
        )


def downgrade() -> None:
    op.drop_table("ecosystem_benchmarks")
    op.drop_table("ecosystem_data_submissions")
    op.drop_table("alert_rules")
    op.drop_table("watched_lanes")
    op.drop_table("forecasts")
    op.drop_table("signals")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("organizations")

    op.execute("DROP TYPE IF EXISTS alertcondition")
    op.execute("DROP TYPE IF EXISTS alertchannel")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
