"""Expose common type aliases for strategy development.

Provide a centralized set of semantic type aliases used across the SDK to improve
readability and consistency when working with market data, orders, and parameters.

These aliases define standard trading concepts such as:
- Symbols representing tradable instruments (e.g., "AAPL").
- Timeframes for historical data (e.g., "1m", "5m", "1d").
- Quantities expressed in shares or units.
- Prices and cash values expressed in USD.
- Percent values expressed as numeric ratios (e.g., 0.05 for 5%).
- Flexible inputs for symbol lists, timestamps, and parameters.

Using these aliases helps ensure consistent interpretation of:
- Units (shares, USD, percentages)
- Time granularity (intraday vs daily)
- Input formats (single vs multiple symbols, datetime vs string)

Notes:
- Historical data retrieved using these types is ordered from oldest to newest.
- Timeframes follow standard bar intervals such as "1m", "5m", "15m", "1h", and "1d".
- Timestamp and date inputs may be provided as datetime objects or ISO-formatted strings.
"""
from .aliases import (
    Symbol,
    InstrumentId,
    Timeframe,
    Timestamp,
    TimestampLike,
    DateLike,
    QuantityValue,
    PriceValue,
    CashValue,
    PercentValue,
    OrderId
)

__all__ = [
    "Symbol",
    "InstrumentId",
    "Timeframe",
    "Timestamp",
    "TimestampLike",
    "DateLike",
    "QuantityValue",
    "PriceValue",
    "CashValue",
    "PercentValue",
    "OrderId"
]
