from __future__ import annotations

from dataclasses import dataclass
import numpy as np

@dataclass
class _BarRow:
    ts: np.datetime64
    open: np.float64
    high: np.float64
    low: np.float64
    close: np.float64
    volume: np.float64

@dataclass
class _TickRow:
    """
    Internal runtime contract for tick data.

    Represents a single trade execution event.
    """

    ts: np.datetime64
    price: np.float64
    volume: np.float64

@dataclass
class _QuoteRow:
    """
    Internal runtime contract for quote data.

    Represents a snapshot of market bid/ask liquidity.
    """

    ts: np.datetime64
    bid_price: np.float64
    ask_price: np.float64
    bid_size: np.float64
    ask_size: np.float64