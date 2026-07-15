from __future__ import annotations

from abc import ABC, abstractmethod

from alphovex_sdk import(
    Timeframe,
)

from contracts.rows import _BarRow

class HistoricalDataClientPort(ABC):
    @abstractmethod
    async def get_bar_history(
        self,
        symbol: str,
        timeframe: Timeframe,
        window: int
    ) -> list[_BarRow] | None:
        ...
    