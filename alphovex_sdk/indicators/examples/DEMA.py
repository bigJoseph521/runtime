from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class DEMA(Indicator):
    """
    Calculate the Double Exponential Moving Average.

    DEMA is calculated as:

    ``2 * EMA(price) - EMA(EMA(price))``

    Bars must be ordered from newest to oldest. Completed state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_period",
        "_price_type",
        "_alpha",
        "_ema1",
        "_ema2",
    )

    def __init__(
        self,
        period: int = 14,
        shift: int = 0,
        price_type: str = "close",
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        if type(shift) is not int:
            raise InvalidValueError(
                "'shift' must be an integer"
            )

        validate_price_type(price_type)

        self._period = period
        self._price_type = price_type
        self._alpha = 2.0 / (period + 1.0)

        self._ema1: float | None = None
        self._ema2: float | None = None

    @property
    def required_history(self) -> int:
        return max(1, 2 * self._period - 2)

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        if self._period == 1:
            return PriceValue(current_price)

        if self._ema1 is None:
            ema1: float | None = None
            ema2: float | None = None
            count = 0

            for index in range(
                self.required_history - 1,
                0,
                -1,
            ):
                price = float(
                    bars[index].get_price(
                        self._price_type
                    )
                )

                if ema1 is None:
                    ema1 = price
                else:
                    ema1 += self._alpha * (
                        price - ema1
                    )

                count += 1

                if count == self._period:
                    ema2 = ema1
                elif count > self._period:
                    ema2 += self._alpha * (
                        ema1 - ema2
                    )

            self._ema1 = ema1
            self._ema2 = ema2

        elif is_new_bar:
            completed_price = float(
                bars[1].get_price(self._price_type)
            )

            self._ema1 += self._alpha * (
                completed_price - self._ema1
            )

            self._ema2 += self._alpha * (
                self._ema1 - self._ema2
            )

        current_ema1 = (
            self._ema1
            + self._alpha
            * (current_price - self._ema1)
        )

        current_ema2 = (
            self._ema2
            + self._alpha
            * (current_ema1 - self._ema2)
        )

        return PriceValue(
            2.0 * current_ema1 - current_ema2
        )