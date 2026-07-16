from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final
from collections.abc import Mapping

from ..models import (
    Bar,
    FinancialFactor,
    Quote,
    Tick,
)
from ..typedefs.aliases import PriceValue, Symbol, Timeframe


DEFAULT_BAR_LIMIT: Final[int] = 500
MAX_BAR_LIMIT: Final[int] = 5000
DEFAULT_TRADE_LIMIT: Final[int] = 500
MAX_TRADE_LIMIT: Final[int] = 5000


class DataContext(ABC):
    """
    Provide strategy code with normalized market and symbol data.

    The data context exposes historical and real-time market data, including
    bars, trades, quotes, daily stock summary(OHLCV) and fundamentals.

    Data returned by this context uses SDK models and canonical SDK field
    names. Strategy code should not depend on broker-specific or
    data-provider-specific response formats.

    Notes
    -----
    Methods that return multiple market-data observations order them from
    newest to oldest:

    ```python
    data[0]   # Newest observation
    data[1]   # Previous observation
    data[-1]  # Oldest returned observation
    ```

    The runtime owns and updates the underlying data. Strategy code should
    treat returned models and arrays as read-only snapshots.
    """

    @abstractmethod
    def get_latest_bars(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        start: int,
        count: int,
        limit: int | None = None,
    ) -> tuple[Bar, ...]:
        """
        Return recent bars for a symbol and timeframe.

        Bars are ordered from newest to oldest. ``start=0`` refers to the
        newest available bar.

        Parameters
        ----------
        symbol
            Trading symbol whose bars are requested.
        timeframe
            Timeframe of the requested bars.
        start
            Zero-based offset from the newest available bar.
        count
            Maximum number of bars to return.
        limit
            Optional upper bound on the number of bars that may be returned.
            When omitted, the runtime applies its configured default limit.

        Returns
        -------
        tuple[Bar, ...]
            Bars ordered from newest to oldest. Returns an empty tuple when no
            matching bars are available.

        Raises
        ------
        ValueError
            Raised when ``start`` is negative, ``count`` is less than one, or
            ``limit`` exceeds ``MAX_BAR_LIMIT``.

        Examples
        --------
        ```python
        bars = self.data.get_latest_bars(
            symbol="AAPL",
            timeframe="1m",
            start=0,
            count=20,
        )

        if bars:
            newest_bar = bars[0]
        ```
        """
        ...

    @abstractmethod
    def get_latest_trades(
        self,
        symbol: Symbol,
        *,
        start: int,
        count: int,
        limit: int | None = None,
    ) -> tuple[Tick, ...]:
        """
        Return recent executed trades for a symbol.

        Trades are ordered from newest to oldest. ``start=0`` refers to the
        newest available trade.

        Parameters
        ----------
        symbol
            Trading symbol whose trades are requested.
        start
            Zero-based offset from the newest available trade.
        count
            Maximum number of trades to return.
        limit
            Optional upper bound on the number of trades that may be returned.
            When omitted, the runtime applies its configured default limit.

        Returns
        -------
        tuple[Tick, ...]
            Executed trades ordered from newest to oldest. Returns an empty
            tuple when no matching trades are available.

        Raises
        ------
        ValueError
            Raised when ``start`` is negative, ``count`` is less than one, or
            ``limit`` exceeds ``MAX_TRADE_LIMIT``.
        """
        ...

    @abstractmethod
    def get_latest_trade(
        self,
        symbol: Symbol,
    ) -> Tick | None:
        """
        Return the most recent executed trade for a symbol.

        Parameters
        ----------
        symbol
            Trading symbol whose latest trade is requested.

        Returns
        -------
        Tick | None
            Most recent executed trade, or ``None`` when no trade data is
            available.
        """
        ...

    @abstractmethod
    def get_current_bar(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Bar | None:
        """
        Return the current forming bar.

        Parameters
        ----------
        symbol
            Trading symbol whose current bar is requested.
        timeframe
            Timeframe of the requested bar.

        Returns
        -------
        Bar | None
            Current incomplete bar, or ``None`` when no forming bar is
            available.

        Notes
        -----
        The returned bar may change as additional trades arrive before the
        timeframe interval closes.
        """
        ...

    @abstractmethod
    def is_new_bar(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> bool:
        """
        Return whether a new bar has started for the specified market-data stream.

        A new bar starts when the runtime receives the first update belonging to a
        new timeframe interval. At that point, the previous bar is considered
        completed.

        Parameters
        ----------
        symbol
            Trading symbol to check.
        timeframe
            Bar timeframe to check.

        Returns
        -------
        bool
            ``True`` during the runtime event cycle in which a new bar is detected;
            otherwise ``False``.

        Notes
        -----
        This method reports a transition between bar intervals, not whether a
        partially forming bar currently exists.

        The signal is typically available only for the runtime event cycle that
        caused the new bar to start. Its exact lifetime is controlled by the
        runtime implementation.
        """
        ...

    @abstractmethod
    def get_latest_quote(
        self,
        symbol: Symbol,
    ) -> Quote:
        """
        Return the latest bid-and-ask quote for a symbol.

        Parameters
        ----------
        symbol
            Trading symbol whose quote is requested.

        Returns
        -------
        Quote
            Latest available quote.

        Raises
        ------
        LookupError
            Raised when no quote is available for the symbol.
        """
        ...

    @abstractmethod
    def get_best_bid(
        self,
        symbol: Symbol,
    ) -> PriceValue | None:
        """
        Return the latest best bid price.

        Parameters
        ----------
        symbol
            Trading symbol whose bid price is requested.

        Returns
        -------
        PriceValue | None
            Highest currently available bid price, or ``None`` when quote data
            is unavailable.
        """
        ...

    @abstractmethod
    def get_best_ask(
        self,
        symbol: Symbol,
    ) -> PriceValue | None:
        """
        Return the latest best ask price.

        Parameters
        ----------
        symbol
            Trading symbol whose ask price is requested.

        Returns
        -------
        PriceValue | None
            Lowest currently available ask price, or ``None`` when quote data
            is unavailable.
        """
        ...

    @abstractmethod
    def get_spread(
        self,
        symbol: Symbol,
    ) -> PriceValue | None:
        """
        Return the latest bid-ask spread.

        The spread is calculated as:

        ``best_ask - best_bid``

        Parameters
        ----------
        symbol
            Trading symbol whose spread is requested.

        Returns
        -------
        PriceValue | None
            Difference between the best ask and best bid prices, or ``None``
            when quote data is unavailable.
        """
        ...

    @abstractmethod
    def get_daily_summaries(
        self,
        symbols: list[str] | str = "ALL",
    ) -> Mapping[str, Bar] | None:
        """
        Return the previous day's stock summary by symbol.

        Parameters
        ----------
        symbols
            Symbols whose daily summaries are requested, or ``"ALL"`` to request
            every available symbol.

        Returns
        -------
        Mapping[str, Bar] | None
            Mapping from each symbol to its daily OHLCV bar, or ``None`` when no
            daily summary data is available.
        """
        ...

    @abstractmethod
    def get_fundamentals(
        self,
        fields: list[FinancialFactor] | str = "ALL",
        symbols: list[str] | str = "ALL",
    ) -> Mapping[FinancialFactor, Mapping[str, float]] | None:
        """
        Return fundamental values grouped by financial factor.

        Parameters
        ----------
        fields
            Financial factors to return, or ``"ALL"`` to return every available
            financial factor.
        symbols
            Symbols to return, or ``"ALL"`` to return every available symbol.

        Returns
        -------
        Mapping[FinancialFactor, Mapping[str, float]] | None
            Mapping from each financial factor to a symbol-value mapping, or
            ``None`` when fundamental data is unavailable.

        Examples
        --------
        ```python
        fundamentals = self.data.fundamentals(
            fields=[
                FinancialFactor.PE_RATIO,
                FinancialFactor.MARKET_CAP,
            ],
            symbols=["AAPL", "MSFT"],
        )

        if fundamentals is not None:
            apple_pe = fundamentals[FinancialFactor.PE_RATIO]["AAPL"]
        """
        ...