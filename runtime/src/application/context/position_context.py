from __future__ import annotations

from typing import Any

from alphovex_sdk import(
    Position,
    PositionContext,
    Symbol
)

class RuntimePositionContext(PositionContext):
    def __init__(
        self,
        positions: list[Position] | None = None,
    ) -> None:
        """Initialize the context from the deployment position snapshot."""
        self._positions = list(positions or [])
    
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
        
