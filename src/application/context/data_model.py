from __future__ import annotations

import numpy as np

from contracts.rows import (
    _BarRow,
    _TickRow
)

class BarRingBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.size = 0
        self.head = 0

        self.ts = np.zeros(capacity, dtype="datetime64[ms]")
        self.open = np.zeros(capacity, dtype=np.float64)
        self.high = np.zeros(capacity, dtype=np.float64)
        self.low = np.zeros(capacity, dtype=np.float64)
        self.close = np.zeros(capacity, dtype=np.float64)
        self.volume = np.zeros(capacity, dtype=np.float64)
        
    def append(
        self,
        bar: _BarRow
    ):
        i = self.head

        self.ts[i] = bar.ts
        self.open[i] = bar.open
        self.high[i] =  bar.high
        self.low[i] = bar.low
        self.close[i] = bar.close
        self.volume[i] = bar.volume
    
        self.head = (self.head + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def get_field(self, name: str) -> np.ndarray:
        if name == "ts":
            return self.ts
        elif name == "open":
            return self.open
        elif name == "high":
            return self.high
        elif name == "low":
            return self.low
        elif name == "close":
            return self.close
        elif name == "volume":
            return self.volume
        else:
            raise ValueError(f"Unknown field: {name}")
        
    def view(self, field: str) -> np.ndarray:
        """
        Return newest-first array
        """
        arr = self.get_field(field)

        if self.size == 0:
            return np.empty(0, dtype=arr.dtype)

        if self.size < self.capacity:
            return arr[:self.size][::-1]

        head = self.head

        return np.concatenate([
            arr[head:],
            arr[:head]
        ])[::-1]
    
    def update_current_bar(
        self,
        bar: _BarRow
    ):
        i = self.head

        self.ts[i] = bar.ts
        self.open[i] = bar.open
        self.high[i] =  bar.high
        self.low[i] = bar.low
        self.close[i] = bar.close
        self.volume[i] = bar.volume

class TickRingBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.size = 0
        self.head = 0

        # Core tick data
        self.ts = np.zeros(capacity, dtype="datetime64[ms]")
        self.price = np.zeros(capacity, dtype=np.float64)
        self.volume = np.zeros(capacity, dtype=np.float64)

        # Optional derived fields (useful later, still cheap to store)
        self.notional = np.zeros(capacity, dtype=np.float64)

    def append(
        self,
        tick: _TickRow
    ):
        i = self.head

        self.ts[i] = tick.ts
        self.price[i] = tick.price
        self.volume[i] = tick.volume

        # derived metric (useful for VWAP / flow)
        self.notional[i] = tick.price * tick.volume

        self.head = (self.head + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def get_field(self, name=str) -> np.ndarray:
        if name == "ts":
            return self.ts
        elif name == "price":
            return self.price
        elif name == "volume":
            return self.volume
        else:
            return ValueError(f"Unknown field: {name}")
    
    def view(self, name:str) -> np.ndarray:
        arr = self.get_field(name)

        if self.size==0:
            return np.empty(0, dtype=arr.dtype)

        if self.size < self.capacity:
            return arr[:self.size][::-1]

        head = self.head

        return np.concatenate([
            arr[head:],
            arr[:head]
        ])[::-1]
    

    