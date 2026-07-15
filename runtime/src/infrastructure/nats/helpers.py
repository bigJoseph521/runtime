from __future__ import annotations

from typing import Any

from datetime import datetime, timezone
import numpy as np

from alphovex_sdk import Symbol

from contracts.rows import _TickRow, _QuoteRow, _BarRow

def from_raw_1m_bar_to_tick(raw_1m_bar : list) -> tuple[Symbol, _TickRow]:
    new_tick = _TickRow(
        ts = to_numpy_datetime64_utc(raw_1m_bar[2]),
        price = np.float64(raw_1m_bar[3]),
        volume= np.float64(raw_1m_bar[4])
    )

    return raw_1m_bar[1], new_tick


def from_raw_1m_bar_to_bar(raw_1m_bar : list) -> tuple[Symbol, _BarRow]:
    new_bar = _BarRow(
        ts = to_numpy_datetime64_utc(raw_1m_bar[2]),
        open=np.float64(raw_1m_bar[5]),         
        high=np.float64(raw_1m_bar[6]),        
        low=np.float64(raw_1m_bar[7]),        
        close=np.float64(raw_1m_bar[8]),       
        volume=np.float64(raw_1m_bar[9]),
    )    
    return raw_1m_bar[1], new_bar

def from_raw_custom_bar_to_bar(raw_bar : list) -> tuple[Symbol, _BarRow]:
    new_bar = _BarRow(
        ts = to_numpy_datetime64_utc(raw_bar[2]),
        open=np.float64(raw_bar[3]),         
        high=np.float64(raw_bar[4]),        
        low=np.float64(raw_bar[5]),        
        close=np.float64(raw_bar[6]),       
        volume=np.float64(raw_bar[7]),
    )    
    return raw_bar[1], new_bar


def  from_raw_quote_to_quote(raw_quote: list) -> tuple[Symbol, _QuoteRow]:
    new_quote = _QuoteRow(
        ts= to_numpy_datetime64_utc(raw_quote[2]),
        bid_price= np.float64(raw_quote[3]),
        bid_size= np.float64(raw_quote[4]),
        ask_price= np.float64(raw_quote[5]),
        ask_size= np.float64(raw_quote[6])
    )

    return raw_quote[1], new_quote

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