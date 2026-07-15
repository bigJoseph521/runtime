"""Common type aliases used across the Alphovex SDK.

This module defines reusable type aliases to improve readability,
consistency, and developer experience when working with SDK APIs.

The aliases group commonly used concepts such as symbols, timestamps,
numeric values, and input formats into clearly named types, making
function signatures easier to understand without changing runtime behavior.

All aliases are purely for type checking and documentation purposes and
do not introduce new runtime types.
"""
from __future__ import annotations

from uuid import UUID
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, Literal, TypeAlias

# Symbol-related aliases
Symbol: TypeAlias = str
InstrumentId: TypeAlias = str

# Time-related aliases
Timeframe: TypeAlias = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
Timestamp: TypeAlias = datetime
TimestampLike: TypeAlias = datetime | str
DateLike: TypeAlias = date | str

# Numeric aliases
QuantityValue: TypeAlias = float
PriceValue: TypeAlias = float
CashValue: TypeAlias = float
PercentValue: TypeAlias = float

# Order-related aliases
OrderId: TypeAlias = UUID

