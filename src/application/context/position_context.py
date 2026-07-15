from __future__ import annotations

from typing import Any

from alphovex_sdk import(
    Position,
    PositionContext,
    Symbol
)

from .data_context import RuntimeDataContext

class RuntimePositionContext(PositionContext):
    def __init__(
        self,
        data_context: RuntimeDataContext
    ):
        self._positions : list[Position] = []
        self._data_context = data_context
    
    def get_all_positions(self) -> tuple[Position, ...]:
        return tuple(self._positions)

    def get_positions_for_symbol(self, symbol: str) -> Position | None:
        for p in self._positions:
            if p.symbol == symbol:
                return p
        return None
    
    def update_positions(
        self,
        order_update_info: dict[str, Any]  
    ) -> None:
        ...
        
