from __future__ import annotations

from collections import deque

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class ATR(Indicator):
    """
    Calculate the Average True Range using a rolling simple average.

    Bars must be ordered from newest to oldest. Completed state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_period",
        "_true_ranges",
        "_true_range_sum",
        "_previous_close",
    )

    def __init__(
        self,
        period: int = 14,
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        self._period = period
        self._true_ranges: deque[float] = deque()
        self._true_range_sum = 0.0
        self._previous_close: float | None = None

    @property
    def required_history(self) -> int:
        return self._period + 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        if self._previous_close is None:
            previous_close = float(
                bars[self._period].close
            )

            for index in range(
                self._period - 1,
                0,
                -1,
            ):
                bar = bars[index]
                true_range = self._true_range(
                    bar,
                    previous_close,
                )

                self._true_ranges.append(true_range)
                self._true_range_sum += true_range
                previous_close = float(bar.close)

            self._previous_close = previous_close

        elif is_new_bar:
            bar = bars[1]
            true_range = self._true_range(
                bar,
                self._previous_close,
            )

            if self._period > 1:
                self._true_range_sum -= (
                    self._true_ranges.popleft()
                )
                self._true_ranges.append(true_range)
                self._true_range_sum += true_range

            self._previous_close = float(bar.close)

        current_true_range = self._true_range(
            bars[0],
            self._previous_close,
        )

        return PriceValue(
            (
                self._true_range_sum
                + current_true_range
            )
            / self._period
        )

    @staticmethod
    def _true_range(
        bar: Bar,
        previous_close: float,
    ) -> float:
        high = float(bar.high)
        low = float(bar.low)

        return max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )