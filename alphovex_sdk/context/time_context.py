from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..typedefs import Timestamp, Symbol
from ..models import MarketStatus

class TimeContext(ABC):
    @abstractmethod
    def now(self) -> Timestamp:
        """
        Return the current timestamp.

        Returns
        -------
        Timestamp
            Current timestamp.
        """
        ...

    @abstractmethod
    def today(self) -> date:
        """
        Return the current date.

        Returns
        -------
        date
            Current date.
        """
        ...
    
    @abstractmethod
    def set_timer(
        self,
        interval: int
    ):
        """
        Set timer with minutes
        """
        ...
    
    @abstractmethod
    def current_session(
        self,
        symbol: Symbol | None = None
    ) -> MarketStatus:
        """
        Return the current session snapshot
        """
        ...

    @abstractmethod
    def is_market_open(
        self,
        symbol: Symbol | None = None
    ) -> bool:
        """
        Return whether the symbol or venue is tradable
        """
        ...
    
