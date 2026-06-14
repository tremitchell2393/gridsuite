"""
Pydantic schemas for Signal endpoints — request/response shapes.

Kept separate from ORM models (app/models/) per standard FastAPI
practice: ORM models define DB structure, schemas define API contracts.
This separation matters here specifically because `metadata_json` (DB
column name, avoids clashing with SQLAlchemy's reserved `metadata`
attribute) is exposed to API consumers simply as `metadata`.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_id: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    value: float
    unit: str
    source: str
    confidence: float
    metadata: dict = {}

    @classmethod
    def from_orm_with_metadata(cls, obj):
        """ORM's `metadata_json` -> schema's `metadata`."""
        return cls(
            signal_id=obj.signal_id,
            entity_type=obj.entity_type,
            entity_id=obj.entity_id,
            timestamp=obj.timestamp,
            value=obj.value,
            unit=obj.unit,
            source=obj.source,
            confidence=obj.confidence,
            metadata=obj.metadata_json,
        )


class SignalListResponse(BaseModel):
    entity_type: str
    entity_id: str
    signals: list[SignalRead]
