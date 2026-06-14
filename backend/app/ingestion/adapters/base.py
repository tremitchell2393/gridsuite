"""
Base adapter contract for signal ingestion.

THE CORE PATTERN: every data source gets one adapter class. An adapter's
job is: fetch raw data from its source, transform it into a list of
SignalRecord objects (the universal schema), and return them. Nothing
else — adapters don't write to the database directly (the ingestion
runner does that, see app/ingestion/runner.py), and they don't know
about each other.

This means adding a new signal source is:
  1. Write a new adapter class implementing `fetch()`
  2. Register it in app/ingestion/adapters/__init__.py
  3. Done — the runner, signal store, and modeling layer need no changes.

See Technical Architecture doc, section 2 & 9 (principle 1).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SignalRecord:
    """
    One row in the universal signal schema (mirrors app.models.signal.Signal,
    minus DB-generated fields like `id` and `ingested_at`).
    """
    signal_id: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    value: float
    unit: str
    source: str
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


class BaseAdapter(ABC):
    """
    Subclass this for every new signal source.

    `source_name` should be a short, stable identifier (used as the
    `source` field on every SignalRecord this adapter produces, and as
    the key for raw-data storage paths).
    """

    source_name: str

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> list[SignalRecord]:
        """
        Fetch new data from the source and return it as SignalRecords.

        `since` is the timestamp of the last successful ingestion run for
        this adapter (None on first run) — adapters should use this to
        avoid re-fetching/re-processing data they've already handled,
        where the source API supports it.

        Implementations should raise on unrecoverable errors (the runner
        handles retries via tenacity) and should NOT swallow exceptions
        silently — a failed adapter should be visible in ingestion logs.
        """
        raise NotImplementedError

    def land_raw(self, raw_data: bytes | str, identifier: str) -> str:
        """
        Helper to write raw fetched data to the object storage landing
        zone before transformation, per principle 2 in the architecture
        doc ("raw data is always preserved").

        Returns the storage path written to. Stubbed here — wire up to
        S3/R2 client in app/ingestion/storage.py when ready.
        """
        from app.ingestion.storage import write_raw

        return write_raw(source=self.source_name, identifier=identifier, data=raw_data)
