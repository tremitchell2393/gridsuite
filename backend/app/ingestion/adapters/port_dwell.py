"""
Port Dwell Time adapter.

Signal produced: `port_dwell_time`
Entity type: "port" (e.g. "SHSE", "LAX")

Simpler adapter than CustomsVelocityAdapter — fewer derived fields,
shown here partly to demonstrate how lightweight a new adapter can be
once the pattern is established.
"""
from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.ingestion.adapters.base import BaseAdapter, SignalRecord

PORT_DATA_API_BASE_URL = "https://api.example-port-data.com/v1"


class PortDwellTimeAdapter(BaseAdapter):
    source_name = "port_dwell"

    TRACKED_PORTS = ["SHSE", "LAX", "RTM", "BUSAN", "HOU"]

    def fetch(self, since: datetime | None = None) -> list[SignalRecord]:
        records: list[SignalRecord] = []
        now = datetime.now(UTC)

        for port_code in self.TRACKED_PORTS:
            raw = self._fetch_raw(port_code)

            self.land_raw(
                raw_data=str(raw),
                identifier=f"{port_code}_{now.strftime('%Y%m%dT%H%M%S')}.json",
            )

            records.append(
                SignalRecord(
                    signal_id="port_dwell_time",
                    entity_type="port",
                    entity_id=port_code,
                    timestamp=now,
                    value=raw["avg_dwell_days"],
                    unit="days",
                    source=self.source_name,
                    confidence=1.0,
                    metadata={
                        "vessels_at_anchorage": raw.get("vessels_at_anchorage", 0),
                        "baseline_30d_avg": raw.get("baseline_30d_avg_days"),
                    },
                )
            )

        return records

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def _fetch_raw(self, port_code: str) -> dict:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{PORT_DATA_API_BASE_URL}/ports/{port_code}/dwell-time",
                headers={"Authorization": f"Bearer {settings.AIS_API_KEY}"},
            )
            response.raise_for_status()
            return response.json()
