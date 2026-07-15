from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class CCI(Indicator):
    """
    Calculate the Commodity Channel Index.

    CCI is calculated as:

    ``(price - average) / (0.015 * mean_deviation)``

    Bars must be ordered from newest to oldest.
    """

    __slots__ = (
        "_period",
        "_price_type",
    )

    def __init__(
        self,
        period: int = 14,
        price_type: str = "typical",
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        validate_price_type(price_type)

        self._period = period
        self._price_type = price_type

    @property
    def required_history(self) -> int:
        return self._period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self._period:
            return None

        total = 0.0

        for index in range(self._period):
            total += float(
                bars[index].get_price(self._price_type)
            )

        average = total / self._period
        mean_deviation = 0.0

        for index in range(self._period):
            price = float(
                bars[index].get_price(self._price_type)
            )

            mean_deviation += abs(price - average)

        mean_deviation /= self._period

        if mean_deviation == 0.0:
            return PriceValue(0.0)

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        return PriceValue(
            (current_price - average)
            / (0.015 * mean_deviation)
        )