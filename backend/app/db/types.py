"""
Portable column types.

JSONB on Postgres / JSON elsewhere, and UUID-as-native-on-Postgres /
UUID-as-string-on-SQLite. Keeps model definitions database-agnostic for
the test suite (SQLite) while using native types in production
(Postgres + Timescale).
"""
import uuid as uuid_module

from sqlalchemy import CHAR, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


class PortableJSON(TypeDecorator):
    """JSONB on Postgres, JSON everywhere else."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class PortableUUID(TypeDecorator):
    """Native UUID on Postgres, CHAR(36) string on everything else (e.g. SQLite)."""

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        if isinstance(value, uuid_module.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return value
        return uuid_module.UUID(value)
