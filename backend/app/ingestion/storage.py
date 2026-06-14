"""
Raw data storage — the "land everything before processing" layer.

At MVP this can write to local disk (useful for dev/testing); in
production it writes to S3/R2. Either way, the interface adapters use
(`write_raw`) doesn't change — see app.ingestion.adapters.base.BaseAdapter.land_raw.
"""
import os
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings

LOCAL_RAW_DATA_DIR = Path(os.environ.get("LOCAL_RAW_DATA_DIR", "./data/raw"))


def write_raw(source: str, identifier: str, data: bytes | str) -> str:
    """
    Write raw ingested data, organized by source and ingestion date.

    Path shape: {source}/{YYYY-MM-DD}/{identifier}
    e.g. "ais_marinetraffic/2025-01-15/vessels_batch_001.json"

    Returns the path/key the data was written to.
    """
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    relative_path = f"{source}/{date_str}/{identifier}"

    if settings.S3_ACCESS_KEY:
        return _write_to_s3(relative_path, data)
    return _write_to_local(relative_path, data)


def _write_to_local(relative_path: str, data: bytes | str) -> str:
    full_path = LOCAL_RAW_DATA_DIR / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    mode = "wb" if isinstance(data, bytes) else "w"
    with open(full_path, mode) as f:
        f.write(data)

    return str(full_path)


def _write_to_s3(relative_path: str, data: bytes | str) -> str:
    import boto3

    client = boto3.client(
        "s3",
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL or None,
    )

    body = data.encode("utf-8") if isinstance(data, str) else data
    client.put_object(Bucket=settings.S3_BUCKET, Key=relative_path, Body=body)

    return f"s3://{settings.S3_BUCKET}/{relative_path}"
