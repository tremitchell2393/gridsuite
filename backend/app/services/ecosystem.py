"""
Ecosystem data aggregation service.

This is where the "hard architectural boundary" from
app/models/ecosystem.py is enforced in code: this is the ONLY function
that reads EcosystemDataSubmission rows, and it writes out only
aggregate statistics (median/p25/p75 across organizations) to
EcosystemBenchmark.

MIN_CONTRIBUTORS_FOR_BENCHMARK enforces k-anonymity — a benchmark is
only published if enough distinct organizations contributed data for
that data_type/lane/period, so no single contributor's value can be
reverse-engineered from the aggregate.
"""
import logging
from datetime import date, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.ecosystem import EcosystemBenchmark, EcosystemDataSubmission

logger = logging.getLogger(__name__)

MIN_CONTRIBUTORS_FOR_BENCHMARK = 5


def compute_weekly_benchmarks(week_end: date | None = None) -> int:
    """
    Compute and store benchmarks for the most recently completed week
    (or the week ending `week_end`, for backfills/testing).

    Returns the number of benchmark rows written.
    """
    db = SessionLocal()
    written = 0

    if week_end is None:
        week_end = date.today()
    week_start = week_end - timedelta(days=7)

    try:
        # Group submissions by (data_type, lane_id) for the period
        groups = _get_submission_groups(db, week_start, week_end)

        for (data_type, lane_id), submissions in groups.items():
            org_ids = {s.organization_id for s in submissions}

            if len(org_ids) < MIN_CONTRIBUTORS_FOR_BENCHMARK:
                logger.info(
                    "Skipping benchmark for %s/%s — only %d contributors (need %d)",
                    data_type, lane_id, len(org_ids), MIN_CONTRIBUTORS_FOR_BENCHMARK,
                )
                continue

            values = np.array([s.value for s in submissions])
            unit = submissions[0].unit

            benchmark = EcosystemBenchmark(
                data_type=data_type,
                lane_id=lane_id,
                period_start=week_start,
                period_end=week_end,
                median_value=float(np.median(values)),
                p25_value=float(np.percentile(values, 25)),
                p75_value=float(np.percentile(values, 75)),
                unit=unit,
                contributor_count=len(org_ids),
            )
            db.add(benchmark)
            written += 1

        db.commit()
    finally:
        db.close()

    logger.info("Computed %d ecosystem benchmarks for week ending %s", written, week_end)
    return written


def _get_submission_groups(
    db: Session, week_start: date, week_end: date
) -> dict[tuple[str, str | None], list[EcosystemDataSubmission]]:
    stmt = select(EcosystemDataSubmission).where(
        EcosystemDataSubmission.period_start >= week_start,
        EcosystemDataSubmission.period_end <= week_end,
    )
    rows = db.execute(stmt).scalars().all()

    groups: dict[tuple[str, str | None], list[EcosystemDataSubmission]] = {}
    for row in rows:
        key = (row.data_type, row.lane_id)
        groups.setdefault(key, []).append(row)

    return groups
