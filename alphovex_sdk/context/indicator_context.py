from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Final

from ..indicators.base import Indicator
from ..typedefs import Symbol, Timeframe


DEFAULT_INDICATOR_HISTORY_SIZE: Final[int] = 100
MIN_INDICATOR_HISTORY_SIZE: Final[int] = 1
MAX_INDICATOR_HISTORY_SIZE: Final[int] = 1000


class IndicatorUpdateMode(StrEnum):
    """
    Define when a registered indicator is updated.

    Members
    -------
    BAR
        Update the indicator when a bar is completed.
    TICK
        Update or preview the indicator when a trade tick arrives.
    """

    BAR = "bar"
    TICK = "tick"


class IndicatorContext(ABC):
    """
    Provide indicator registration and value access to strategy code.

    Each indicator registration is associated with a symbol, timeframe,
    update mode, and bounded output history.

    The value returned by ``register()`` is an opaque platform-managed handle.
    Strategy code should store the returned value and pass it to ``value()``,
    ``values()``, or ``unregister()``. Users do not need to know or depend on
    the handle's internal type or representation.
    """

    @abstractmethod
    def register(
        self,
        indicator: Indicator,
        symbol: Symbol,
        timeframe: Timeframe,
        *,
        update_mode: IndicatorUpdateMode = IndicatorUpdateMode.BAR,
        history_size: int | None = None,
    ) -> Any:
        """
        Register an indicator and return an opaque handle.

        The indicator constructor should contain only formula-specific
        parameters. Symbol, timeframe, update mode, and output-history size
        are registration-level settings.

        Parameters
        ----------
        indicator
            Indicator instance to register.
        symbol
            Symbol whose market data is used by the indicator.
        timeframe
            Timeframe used for indicator calculation.
        update_mode
            Determines when the platform updates the indicator. ``BAR``
            updates the indicator from completed bars. ``TICK`` updates or
            previews the indicator from trade ticks and current-bar data.
        history_size
            Maximum number of calculated indicator outputs retained for this
            registration. When ``None``, the platform uses
            ``DEFAULT_INDICATOR_HISTORY_SIZE``.

        Returns
        -------
        Any
            Opaque platform-managed handle used to read indicator values or
            unregister the indicator.

        Raises
        ------
        InvalidValueError
            Raised when ``symbol``, ``timeframe``, or ``history_size`` is
            invalid.

        Examples
        --------
        ```python
        self.sma_handle = self.indicators.register(
            indicator=SMA(
                window_size=20,
                price_type="close",
            ),
            symbol="AAPL",
            timeframe="1m",
            update_mode=IndicatorUpdateMode.BAR,
            history_size=100,
        )
        ```
        """
        ...

    @abstractmethod
    def get_value(
        self,
        handle: Any,
    ) -> tuple[Any | None, bool]:
        """
        Return the latest indicator value and update status.

        Parameters
        ----------
        handle
            Opaque handle returned by ``register()``.

        Returns
        -------
        tuple[Any | None, bool]
            Two-item tuple containing:

            - latest indicator value, or ``None`` when unavailable
            - ``True`` when the indicator was updated during the current
              runtime event; otherwise ``False``

        Notes
        -----
        An indicator may not update when market data for another symbol
        arrives.

        For example, an AAPL indicator remains unchanged when the current
        event contains only NVDA market data.
        """
        ...

    @abstractmethod
    def get_values(
        self,
        handle: Any,
        *,
        start: int = 0,
        count: int = 1,
    ) -> tuple[Any, ...]:
        """
        Return recent calculated values for an indicator.

        Values are ordered from newest to oldest. ``start=0`` refers to the
        latest stored value.

        Parameters
        ----------
        handle
            Opaque handle returned by ``register()``.
        start
            Zero-based offset from the newest stored value.
        count
            Maximum number of values to return.

        Returns
        -------
        tuple[Any, ...]
            Indicator values ordered from newest to oldest. Returns an empty
            list when the handle is not registered or no values are available.

        Raises
        ------
        InvalidValueError
            Raised when ``start`` is negative or ``count`` is less than one.
        """
        ...

    @abstractmethod
    def unregister(
        self,
        handle: Any,
    ) -> bool:
        """
        Unregister one indicator.

        Parameters
        ----------
        handle
            Opaque handle returned by ``register()``.

        Returns
        -------
        bool
            ``True`` when the indicator was registered and removed; otherwise
            ``False``.
        """
        ...

    @abstractmethod
    def unregister_all(self) -> None:
        """
        Unregister all registered indicators.
        """
        ...