from __future__ import annotations

from typing import Any
import zlib
import numpy as np
from datetime import datetime, timezone
from contracts.rows import _TickRow, _QuoteRow

def calculate_partition(value: str, partition_count: int) -> int:
    """
    ``partition = zlib.crc32(job_id.encode("utf-8")) % partition_count`` (IEEE CRC32).
    """
    if partition_count < 1:
        raise ValueError("partition_count must be >= 1")
    normalized = str(value or "").strip()
    crc = zlib.crc32(normalized.encode("utf-8")) & 0xFFFFFFFF
    return int(crc % partition_count)

def from_raw_to_tick(raw_tick: dict[str, Any]) -> _TickRow:
    new_tick = _TickRow(
        ts = to_numpy_datetime64_utc(raw_tick["time_utc"]),
        price = np.float64(raw_tick["price"]),
        volume= np.float64(raw_tick["size"])
    )

    return new_tick

def  from_raw_to_quote(raw_quote: dict[str, Any]) -> _QuoteRow:
    new_quote = _QuoteRow(
        ts= to_numpy_datetime64_utc(raw_quote["time_utc"]),
        bid_price= np.float64(raw_quote["bid_price"]),
        bid_size= np.float64(raw_quote["bid_size"]),
        ask_price= np.float64(raw_quote["ask_price"]),
        ask_size= np.float64(raw_quote["ask_size"])
    )

    return new_quote

def to_numpy_datetime64_utc(value: str | datetime) -> np.datetime64:
    if isinstance(value, str):
        # Supports ISO-8601 values ending in Z.
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        value = datetime.fromisoformat(normalized)

    if value.tzinfo is None:
        # Because the source field is explicitly named time_utc.
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)

    # np.datetime64 cannot retain timezone metadata.
    utc_naive = value.replace(tzinfo=None)

    return np.datetime64(utc_naive, "ms")