from __future__ import annotations

from collections import deque

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class AwesomeOscillator(Indicator):
    """
    Calculate the Awesome Oscillator using rolling sums.

    Bars must be ordered from newest to oldest. Forming-bar updates do
    not modify completed state.
    """

    __slots__ = (
        "_fast_period",
        "_slow_period",
        "_fast_prices",
        "_slow_prices",
        "_fast_sum",
        "_slow_sum",
    )

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 34,
    ) -> None:
        if type(fast_period) is not int or fast_period < 1:
            raise InvalidValueError(
                "'fast_period' must be a positive integer"
            )

        if type(slow_period) is not int or slow_period < 1:
            raise InvalidValueError(
                "'slow_period' must be a positive integer"
            )

        if fast_period >= slow_period:
            raise InvalidValueError(
                "'fast_period' must be less than 'slow_period'"
            )

        self._fast_period = fast_period
        self._slow_period = slow_period

        self._fast_prices: deque[float] = deque()
        self._slow_prices: deque[float] = deque()

        self._fast_sum = 0.0
        self._slow_sum = 0.0

    @property
    def required_history(self) -> int:
        return self._slow_period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self._slow_period:
            return None

        if not self._slow_prices:
            for index in range(
                self._slow_period - 1,
                0,
                -1,
            ):
                price = float(
                    bars[index].get_price("median")
                )

                self._slow_prices.append(price)
                self._slow_sum += price

                if index < self._fast_period:
                    self._fast_prices.append(price)
                    self._fast_sum += price

        elif is_new_bar:
            price = float(
                bars[1].get_price("median")
            )

            self._slow_sum -= self._slow_prices.popleft()
            self._slow_prices.append(price)
            self._slow_sum += price

            if self._fast_period > 1:
                self._fast_sum -= self._fast_prices.popleft()
                self._fast_prices.append(price)
                self._fast_sum += price

        current_price = float(
            bars[0].get_price("median")
        )

        fast_average = (
            self._fast_sum + current_price
        ) / self._fast_period

        slow_average = (
            self._slow_sum + current_price
        ) / self._slow_period

        return PriceValue(
            fast_average - slow_average
        )