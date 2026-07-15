from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any
from alphovex_sdk.typedefs.aliases import Timeframe, Symbol


class MarketDataPort(ABC):
    def __init__(self):
        ...

    @abstractmethod
    def set_channels(self, ref: list[tuple[Symbol, Timeframe]]):
        ...

    @abstractmethod
    def add_channel(self, symbol: Symbol, timeframe: Timeframe):
        ...

    @abstractmethod
    def remove_channel(self, symbol: Symbol, timeframe: Timeframe):
        ...

    @abstractmethod
    def unsubscribe_all_channels(self):
        ...
    
    @abstractmethod
    async def start(self):
        ...
    
    @abstractmethod
    async def restart(self):
        ...
    
    @abstractmethod
    async def stop(self):
        ...