from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import Bar


class Indicator(ABC):
    """
    Define the public interface for custom indicators.

    Strategy developers may extend this class to implement custom indicator
    calculation logic.

    The runtime uses ``required_history`` to prepare the required bar window
    and calls ``calculate()`` whenever:

    - the current forming bar changes
    - a new bar starts

    The value returned by ``calculate()`` becomes the indicator's latest
    calculated value.

    Notes
    -----
    Indicator implementations may maintain internal calculation state.

    The runtime may create separate indicator instances for different symbols,
    timeframes, or registrations. An indicator instance should therefore
    maintain state only for the market-data stream assigned to that instance.

    The ``bars`` parameter passed to ``calculate()`` is the source of truth.
    Developers can implement an indicator correctly by recalculating its value
    directly from ``bars``.

    Implementations may also store previous calculation values internally to
    reduce repeated work.
    """

    @property
    @abstractmethod
    def required_history(self) -> int:
        """
        Return the minimum number of bars required for calculation.

        The platform uses this value to determine how many bars must be
        available before the indicator can produce its first meaningful
        result.

        The returned number represents the complete calculation window,
        including the current forming bar.

        For example, an SMA with a window size of 20 requires:

        - the current forming bar
        - the previous 19 completed bars

        Therefore, its ``required_history`` is 20.

        Returns
        -------
        int
            Minimum number of bars required to calculate a valid indicator
            value.

        Notes
        -----
        This property must not perform calculations or modify indicator state.
        It should only describe the indicator's bar-data requirement.

        Indicators that require additional initialization, smoothing, or
        stabilization may return a value greater than their primary
        calculation period.

        Examples
        --------
        ```python
        class SMA(Indicator):
            def __init__(self, window_size: int) -> None:
                self._window_size = window_size

            @property
            def required_history(self) -> int:
                return self._window_size
        ```
        """
        ...

    @abstractmethod
    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> Any | None:
        """
        Calculate and return the latest indicator value.

        The runtime calls this method whenever the current forming bar changes
        or a new bar starts.

        An indicator can be implemented correctly by recalculating its value
        directly from ``bars`` on every call.

        For improved performance, an implementation may maintain internal
        calculation state, such as:

        - the previous current-bar price
        - the previous oldest price
        - a rolling sum
        - a previously calculated EMA value

        Parameters
        ----------
        bars
            Bars ordered from newest to oldest.

            For ``IndicatorUpdateMode.BAR``, ``bars[0]`` is the most recently
            completed bar.

            For ``IndicatorUpdateMode.TICK``, ``bars[0]`` is the current forming
            bar, followed by completed bars.

            This parameter contains all data required to calculate the
            indicator correctly.

            Implementations must treat repeated versions of ``bars[0]`` as
            updates to the same forming bar, not as separate bars.

            Implementations must not modify this list or its bar objects.

        is_new_bar
            Indicate whether ``bars[0]`` is a newly started bar.

            When ``False``, ``bars[0]`` is an updated version of the same
            forming bar.

            When ``True``, the previous forming bar has completed and
            ``bars[0]`` is a new forming bar.

            Implementations that calculate directly from ``bars`` may ignore
            this parameter.

            Implementations that maintain internal rolling state may use this
            value to distinguish between:

            - replacing the previous value of the same forming bar
            - advancing the calculation window to a new bar

        Returns
        -------
        Any | None
            Latest calculated indicator value, including the current forming
            bar.

            Returns ``None`` when there are not enough bars to produce a valid
            value.

        Notes
        -----
        There are two valid implementation styles.

        Simple calculation
            Recalculate the value directly from ``bars`` on every call.

            This is the easiest and safest implementation style. It does not
            require internal rolling state or special handling for
            ``is_new_bar``.

            Example for an SMA:

            ```python
            if len(bars) < self._window_size:
                return None

            total = sum(
                bar.close
                for bar in bars[:self._window_size]
            )

            return total / self._window_size
            ```

        Optimized calculation
            Maintain internal rolling state and use ``is_new_bar`` to
            distinguish a new calculation window from an update to the same
            forming bar.

            Example for an optimized SMA:

            ```python
            if len(bars) < self._window_size:
                return None

            current_price = bars[0].close

            if self._rolling_sum is None:
                self._rolling_sum = sum(
                    bar.close
                    for bar in bars[:self._window_size]
                )

            elif is_new_bar:
                self._rolling_sum += (
                    current_price
                    - self._oldest_price
                )

            else:
                self._rolling_sum += (
                    current_price
                    - self._previous_current_price
                )

            self._previous_current_price = current_price
            self._oldest_price = bars[
                self._window_size - 1
            ].close

            return self._rolling_sum / self._window_size
            ```

        Both implementation styles must produce the same result.

        ``bars`` is the authoritative input. Internal state exists only to
        reduce repeated calculation work and improve performance.
        """
        ...