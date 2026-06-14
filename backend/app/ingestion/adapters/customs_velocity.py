"""
Customs Filing Velocity adapter.

Signal produced: `customs_velocity_index`
Entity type: "lane" (e.g. "SHSE-LAX") — derived from origin/destination
country pairs in customs filing data.

This adapter is written against a generic "customs data API" shape.
Swap the `_fetch_raw` implementation for whichever real provider you
integrate (e.g. US Census trade data, ImportGenius-style bill-of-lading
data) — the transformation logic below (computing a velocity index from
filing counts) stays the same.

This file is intentionally heavily commented — it's meant to serve as
the reference implementation new adapters are modeled on.
"""
from datetime import UTC, datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.ingestion.adapters.base import BaseAdapter, SignalRecord

CUSTOMS_API_BASE_URL = "https://api.example-customs-data.com/v1"


class CustomsVelocityAdapter(BaseAdapter):
    source_name = "customs_velocity"

    # Lanes we care about at MVP — maps our lane IDs to the
    # origin/destination country+port codes the source API expects.
    TRACKED_LANES = {
        "SHSE-LAX": {"origin": "CN", "origin_port": "CNSHA", "dest": "US", "dest_port": "USLAX"},
        "SHSE-HOU": {"origin": "CN", "origin_port": "CNSHA", "dest": "US", "dest_port": "USHOU"},
        "SHSE-RTM": {"origin": "CN", "origin_port": "CNSHA", "dest": "NL", "dest_port": "NLRTM"},
    }

    def fetch(self, since: datetime | None = None) -> list[SignalRecord]:
        records: list[SignalRecord] = []
        now = datetime.now(UTC)

        for lane_id, route in self.TRACKED_LANES.items():
            raw = self._fetch_raw(route, since)

            # Land the raw response before transforming, per the
            # "preserve raw data" principle.
            self.land_raw(
                raw_data=str(raw),
                identifier=f"{lane_id}_{now.strftime('%Y%m%dT%H%M%S')}.json",
            )

            velocity_index = self._compute_velocity_index(raw)

            records.append(
                SignalRecord(
                    signal_id="customs_velocity_index",
                    entity_type="lane",
                    entity_id=lane_id,
                    timestamp=now,
                    value=velocity_index,
                    unit="ratio_to_30d_avg",
                    source=self.source_name,
                    confidence=self._confidence_from_raw(raw),
                    metadata={
                        "filing_count_today": raw.get("filing_count", 0),
                        "filing_count_30d_avg": raw.get("filing_count_30d_avg", 0),
                        "origin_port": route["origin_port"],
                        "dest_port": route["dest_port"],
                    },
                )
            )

        return records

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def _fetch_raw(self, route: dict, since: datetime | None) -> dict:
        """
        Fetch raw filing count data for a single route from the source API.

        Retries with exponential backoff on transient failures (network
        errors, 5xx responses). Raises after 3 attempts — the ingestion
        runner logs this as a failed run for this lane without affecting
        other adapters/lanes.
        """
        params = {
            "origin_port": route["origin_port"],
            "dest_port": route["dest_port"],
        }
        if since:
            params["since"] = since.isoformat()

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{CUSTOMS_API_BASE_URL}/filing-volume",
                params=params,
                headers={"Authorization": f"Bearer {settings.CUSTOMS_DATA_API_KEY}"},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _compute_velocity_index(raw: dict) -> float:
        """
        Velocity index = today's filing count relative to the trailing
        30-day average. >1.0 means filings are accelerating (a leading
        indicator of demand increase on this lane).
        """
        today = raw.get("filing_count", 0)
        avg_30d = raw.get("filing_count_30d_avg", 0)

        if avg_30d <= 0:
            return 1.0  # neutral if no baseline yet

        return round(today / avg_30d, 4)

    @staticmethod
    def _confidence_from_raw(raw: dict) -> float:
        """
        Data quality score for this observation. Lower confidence if the
        source flags partial/delayed data (common with customs data,
        which is often revised over several days).
        """
        if raw.get("is_provisional", False):
            return 0.7
        return 1.0
