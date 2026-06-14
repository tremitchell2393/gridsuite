"""
Seed script — generates realistic historical signal data for demo
purposes.

This is NOT one of the production ingestion adapters. It exists purely
to populate the database with plausible-looking data so the dashboard
has something to display before real adapters are connected to live
APIs. Run once: `python -m app.ingestion.seed_demo_data`

Generates 90 days of history for:
  - customs_velocity_index (lane: SHSE-LAX, SHSE-HOU, SHSE-RTM)
  - port_dwell_time (port: SHSE)
  - spot_rate (lane, for dashboard "current value" display)

Also writes one 30-day Forecast per lane (naive-quality, since no model
is trained yet) so the Lane Detail page has a forecast to render.
"""
import logging
import math
import random
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.forecast import Forecast
from app.models.signal import Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

random.seed(42)

LANES = ["SHSE-LAX", "SHSE-HOU", "SHSE-RTM"]
DAYS_OF_HISTORY = 90

# Base spot rates per lane (USD per FEU), used to generate a plausible
# price series with trend + noise.
BASE_RATES = {
    "SHSE-LAX": 2200,
    "SHSE-HOU": 2700,
    "SHSE-RTM": 1900,
}


def generate_customs_velocity(lane_id: str, days: int) -> list[Signal]:
    """
    customs_velocity_index: ratio to 30-day avg, oscillating around 1.0
    with a gentle upward trend toward "now" (simulates accelerating
    demand — the kind of signal that would precede a rate increase).
    """
    now = datetime.now(timezone.utc)
    signals = []

    for i in range(days, 0, -1):
        ts = now - timedelta(days=i)
        trend = 1.0 + (days - i) / days * 0.18  # drifts from 1.0 to ~1.18
        noise = random.gauss(0, 0.03)
        value = round(max(0.7, trend + noise), 4)

        signals.append(
            Signal(
                signal_id="customs_velocity_index",
                entity_type="lane",
                entity_id=lane_id,
                timestamp=ts,
                value=value,
                unit="ratio_to_30d_avg",
                source="customs_velocity",
                confidence=1.0,
                metadata_json={"seeded": True},
            )
        )

    return signals


def generate_port_dwell(port_code: str, days: int) -> list[Signal]:
    """
    port_dwell_time: average days at anchorage, with a recent spike
    (simulates the "+22% vs baseline" congestion story from the
    landing page mock).
    """
    now = datetime.now(timezone.utc)
    signals = []
    baseline = 3.4

    for i in range(days, 0, -1):
        ts = now - timedelta(days=i)
        # Spike in the most recent 14 days
        spike = 0.9 if i <= 14 else 0.0
        noise = random.gauss(0, 0.15)
        value = round(max(1.0, baseline + spike + noise), 2)

        signals.append(
            Signal(
                signal_id="port_dwell_time",
                entity_type="port",
                entity_id=port_code,
                timestamp=ts,
                value=value,
                unit="days",
                source="port_dwell",
                confidence=1.0,
                metadata_json={"seeded": True, "baseline_30d_avg_days": baseline},
            )
        )

    return signals


def generate_spot_rates(lane_id: str, days: int) -> list[Signal]:
    """
    spot_rate: USD per FEU, with a gentle sinusoidal + trend pattern.
    Used for the dashboard's "Current" column.
    """
    now = datetime.now(timezone.utc)
    signals = []
    base = BASE_RATES[lane_id]

    for i in range(days, 0, -1):
        ts = now - timedelta(days=i)
        cycle = math.sin((days - i) / 14) * 0.04
        trend = (days - i) / days * 0.08
        noise = random.gauss(0, 0.01)
        value = round(base * (1 + cycle + trend + noise), 2)

        signals.append(
            Signal(
                signal_id="spot_rate",
                entity_type="lane",
                entity_id=lane_id,
                timestamp=ts,
                value=value,
                unit="usd_per_feu",
                source="seed_demo",
                confidence=1.0,
                metadata_json={"seeded": True},
            )
        )

    return signals


def generate_forecast(lane_id: str) -> Forecast:
    """
    A single 30-day forecast per lane, shaped like what
    rate_forecast.predict_for_lane would produce — but with hand-picked
    values so the demo tells a coherent story (rates trending up on
    the lanes where customs velocity is accelerating, which is all of
    them in this seed, by design).
    """
    now = datetime.now(timezone.utc)
    target_date = (now + timedelta(days=30)).date()

    predicted_pct = round(random.uniform(0.04, 0.14), 4)
    spread = round(random.uniform(0.03, 0.08), 4)

    return Forecast(
        forecast_type="rate_change_pct",
        entity_type="lane",
        entity_id=lane_id,
        generated_at=now,
        target_date=target_date,
        horizon_days=30,
        predicted_value=predicted_pct,
        unit="pct_change",
        lower_bound=round(predicted_pct - spread, 4),
        upper_bound=round(predicted_pct + spread, 4),
        confidence=round(random.uniform(0.65, 0.85), 2),
        model_version="seed_demo_v0",
        signal_attribution=[
            {
                "signal_id": "customs_velocity_index",
                "value": 1.18,
                "baseline_30d": 1.05,
            },
            {
                "signal_id": "port_dwell_time",
                "value": 4.2,
                "baseline_30d": 3.4,
            },
        ],
    )


def main() -> None:
    db = SessionLocal()

    try:
        existing = db.query(Signal).filter(Signal.source == "customs_velocity").count()
        if existing > 0:
            logger.info("Seed data already present (%d customs_velocity rows) — skipping.", existing)
            return

        for lane_id in LANES:
            db.add_all(generate_customs_velocity(lane_id, DAYS_OF_HISTORY))
            db.add_all(generate_spot_rates(lane_id, DAYS_OF_HISTORY))
            db.add(generate_forecast(lane_id))

        # Port dwell is per-port, not per-lane — SHSE is the shared origin
        db.add_all(generate_port_dwell("SHSE", DAYS_OF_HISTORY))

        db.commit()
        logger.info("Seed complete: %d lanes, %d days of history.", len(LANES), DAYS_OF_HISTORY)

    finally:
        db.close()


if __name__ == "__main__":
    main()
