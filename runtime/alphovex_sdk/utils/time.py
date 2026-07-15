"""Time parsing and normalization utilities for the Alphovex SDK.

This module provides reusable helpers for working with time-related values
such as timestamps and dates, using the type aliases defined in
``alphovex_sdk.types.aliases``.

It standardizes how ``TimestampLike`` and ``DateLike`` inputs are handled
by converting them into validated Python ``datetime`` and ``date`` objects.

Key responsibilities include:
- parsing ISO 8601 string inputs into datetime/date objects
- enforcing timezone-aware datetimes
- normalizing all timestamps to UTC
- providing a consistent source of current UTC time

These utilities are intentionally generic and do not include any
trading-specific logic (e.g., market hours or exchange calendars).

All functions are stateless and deterministic, ensuring consistent behavior
across both backtesting and live trading environments.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from alphovex_sdk.typedefs import Timestamp, Timeframe
from alphovex_sdk.errors.validation import InvalidFormatError

def _ensure_utc(value: datetime, *, field_name: str) -> Timestamp:
    """Raise an InvalidFormatError if the datetime is not timezone-aware."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidFormatError.create(
            parameter=field_name,
            expected_format="timezone-aware datetime",
            actual=value,
        )
    
    return value.astimezone(timezone.utc)

def to_datetime(value: Any, *, field_name: str) -> Timestamp:
    """Convert a TimestampLike value into a timezone-aware datetime in UTC."""
    if isinstance(value, datetime):
        return _ensure_utc(value, field_name=field_name)

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            raise InvalidFormatError.create(
                parameter=field_name,
                expected_format="ISO 8601 string",
                actual=value,
            )
        
        return _ensure_utc(parsed, field_name=field_name)
    
    raise InvalidFormatError.create(
        parameter=field_name,
        expected_format="datetime or ISO 8601 string",
        actual=value,
    )

def to_date(value: Any, *, field_name: str) -> date:
    """Convert a DateLike value to a date."""

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidFormatError.create(
                parameter=field_name,
                expected_format="ISO 8601 date string",
                actual=value,
            )

    raise InvalidFormatError.create(
        parameter=field_name,
        expected_format="date or ISO 8601 date string",
        actual=value,
    )

def now_utc() -> Timestamp:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)

def today_utc() -> date:
    """Return the current UTC date."""
    return now_utc().date()

def timeframe_to_timedelta(timeframe: Timeframe) -> timedelta:
    """Convert a timeframe to a timedelta."""
    if timeframe == "1m":
        return timedelta(minutes=1)
    elif timeframe == "5m":
        return timedelta(minutes=5)
    elif timeframe == "15m":
        return timedelta(minutes=15)
    elif timeframe == "30m":
        return timedelta(minutes=30)
    elif timeframe == "1h":
        return timedelta(minutes=60)
    elif timeframe == "1d":
        return timedelta(minutes=1440)


