from __future__ import annotations

from collections import deque
from math import sqrt

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class BB(Indicator):
    """
    Calculate Bollinger Bands using rolling sums.

    Returned tuple order:

    ``middle, upper, lower``

    Completed state is updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_period",
        "_deviation",
        "_price_type",
        "_prices",
        "_sum",
        "_sum_squares",
    )

    def __init__(
        self,
        period: int = 20,
        deviation: float = 2.0,
        shift: int = 0,
        price_type: str = "close",
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        if (
            not isinstance(deviation, (int, float))
            or isinstance(deviation, bool)
            or deviation < 0.0
        ):
            raise InvalidValueError(
                "'deviation' must be non-negative"
            )

        if type(shift) is not int:
            raise InvalidValueError(
                "'shift' must be an integer"
            )

        validate_price_type(price_type)

        self._period = period
        self._deviation = float(deviation)
        self._price_type = price_type

        # Latest period - 1 completed prices, oldest to newest.
        self._prices: deque[float] = deque()
        self._sum = 0.0
        self._sum_squares = 0.0

    @property
    def required_history(self) -> int:
        return self._period + 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
    ] | None:
        if len(bars) < self._period:
            return None

        if self._period > 1 and not self._prices:
            for index in range(
                self._period - 1,
                0,
                -1,
            ):
                price = float(
                    bars[index].get_price(
                        self._price_type
                    )
                )

                self._prices.append(price)
                self._sum += price
                self._sum_squares += price * price

        elif self._period > 1 and is_new_bar:
            price = float(
                bars[1].get_price(
                    self._price_type
                )
            )

            oldest = self._prices.popleft()

            self._sum += price - oldest
            self._sum_squares += (
                price * price
                - oldest * oldest
            )

            self._prices.append(price)

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        total = self._sum + current_price
        total_squares = (
            self._sum_squares
            + current_price * current_price
        )

        middle = total / self._period

        if len(bars) == self._period:
            value = PriceValue(middle)
            return value, value, value

        variance = (
            total_squares / self._period
            - middle * middle
        )

        # Protect against a tiny negative result caused by floating-point
        # subtraction.
        variance = max(variance, 0.0)

        distance = (
            self._deviation
            * sqrt(variance)
        )

        return (
            PriceValue(middle),
            PriceValue(middle + distance),
            PriceValue(middle - distance),
        )