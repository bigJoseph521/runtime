from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class DPO(Indicator):
    """
    Calculate the Detrended Price Oscillator.

    DPO is calculated as:

    ``price - SMA(price, period // 2 + 1)``

    Bars must be ordered from newest to oldest.
    """

    __slots__ = (
        "_ma_period",
        "_price_type",
    )

    def __init__(
        self,
        period: int = 14,
        price_type: str = "close",
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        validate_price_type(price_type)

        self._ma_period = period // 2 + 1
        self._price_type = price_type

    @property
    def required_history(self) -> int:
        return self._ma_period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self._ma_period:
            return None

        total = 0.0

        for index in range(self._ma_period):
            total += float(
                bars[index].get_price(self._price_type)
            )

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        return PriceValue(
            current_price - total / self._ma_period
        )