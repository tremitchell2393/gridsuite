"""
Ingestion runner.

Executes every registered adapter, converts their output to Signal ORM
rows, and writes them to the Signal Store. Designed to be invoked on a
schedule (see app/services/scheduler.py) — one run per day at MVP is
enough for most signal sources; higher-frequency sources (e.g. AIS) can
be scheduled more often once added.

Each adapter runs independently: a failure in one adapter is logged and
does not prevent others from running. This is the "decoupled sources"
principle from the architecture doc in action.
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.ingestion.adapters import ADAPTERS
from app.ingestion.adapters.base import SignalRecord
from app.models.signal import Signal

logger = logging.getLogger(__name__)


def run_all_adapters(since: datetime | None = None) -> dict[str, int]:
    """
    Run every registered adapter once. Returns a summary dict of
    {source_name: records_written} for observability/logging.
    """
    db = SessionLocal()
    summary: dict[str, int] = {}

    try:
        for adapter_cls in ADAPTERS:
            adapter = adapter_cls()
            summary[adapter.source_name] = _run_single_adapter(adapter, db, since)
    finally:
        db.close()

    return summary


def _run_single_adapter(adapter, db: Session, since: datetime | None) -> int:
    """
    Run a single adapter and persist its output. Returns the number of
    records written. Returns 0 (and logs) on failure rather than raising,
    so other adapters in the same run aren't affected.
    """
    try:
        records = adapter.fetch(since=since)
    except Exception:
        logger.exception("Adapter %s failed during fetch()", adapter.source_name)
        return 0

    written = 0
    for record in records:
        try:
            _persist_record(db, record)
            written += 1
        except Exception:
            logger.exception(
                "Failed to persist record from %s: signal_id=%s entity=%s/%s",
                adapter.source_name, record.signal_id, record.entity_type, record.entity_id,
            )

    db.commit()
    logger.info("Adapter %s: wrote %d/%d records", adapter.source_name, written, len(records))
    return written


def _persist_record(db: Session, record: SignalRecord) -> None:
    db.add(
        Signal(
            signal_id=record.signal_id,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            timestamp=record.timestamp,
            value=record.value,
            unit=record.unit,
            source=record.source,
            confidence=record.confidence,
            metadata_json=record.metadata,
        )
    )


if __name__ == "__main__":
    # Manual invocation for local testing: `python -m app.ingestion.runner`
    logging.basicConfig(level=logging.INFO)
    result = run_all_adapters()
    print(f"Ingestion complete: {result}")
