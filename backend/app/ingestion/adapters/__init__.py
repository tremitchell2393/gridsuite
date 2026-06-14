"""
Adapter registry.

ADDING A NEW SIGNAL SOURCE: write your adapter class (see
customs_velocity.py or port_dwell.py for the pattern), then add one line
here. The ingestion runner (app/ingestion/runner.py) picks up everything
in this list automatically — no other code changes needed.

This file is the single point of friction for "fishing for new signals"
to stay cheap, as called out in the architecture doc.
"""
from app.ingestion.adapters.base import BaseAdapter
from app.ingestion.adapters.customs_velocity import CustomsVelocityAdapter
from app.ingestion.adapters.port_dwell import PortDwellTimeAdapter

ADAPTERS: list[type[BaseAdapter]] = [
    CustomsVelocityAdapter,
    PortDwellTimeAdapter,
    # Add new adapters here, e.g.:
    # AISAnomalyAdapter,
    # CarrierBookingAdapter,
    # WeatherDisruptionAdapter,
    # MacroOverlayAdapter,
    # EcosystemDataAdapter,
]
