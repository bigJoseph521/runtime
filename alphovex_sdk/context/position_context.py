from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Position
from ..typedefs import Symbol


class PositionContext(ABC):
    """
    Provide read-only access to current strategy positions.

    Position data is maintained by the platform and exposed as immutable
    snapshots. Strategy code may inspect positions but should not modify them
    to simulate portfolio changes.
    """

    @abstractmethod
    def get_all_positions(self) -> tuple[Position, ...]:
        """
        Return all current positions.

        Returns
        -------
        tuple[Position]
            Current positions known to the platform. Returns an empty tuple
            when no positions exist.
        """
        ...

    @abstractmethod
    def get_positions_for_symbol(
        self,
        symbol: Symbol,
    ) -> Position | None:
        """
        Return current positions for a symbol.

        Parameters
        ----------
        symbol
            Trading symbol whose positions are requested.

        Returns
        -------
        Position | None
            Position associated with the symbol. Returns None when
            no matching positions exist.

        Notes
        -----
        Platform uses one aggregated, next position per symbol
        """
        ...