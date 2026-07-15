from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class Bears(Indicator):
    """
    Calculate Bears Power.

    Bears Power is the current low minus the exponential moving average
    of closing prices.

    Bars must be ordered from newest to oldest. Completed EMA state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_period",
        "_alpha",
        "_ema",
    )

    def __init__(
        self,
        period: int = 13,
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        self._period = period
        self._alpha = 2.0 / (period + 1.0)
        self._ema: float | None = None

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

        if self._ema is None:
            ema = float(
                bars[self._period].close
            )

            for index in range(
                self._period - 1,
                0,
                -1,
            ):
                close = float(
                    bars[index].close
                )

                ema += self._alpha * (
                    close - ema
                )

            self._ema = ema

        elif is_new_bar:
            close = float(
                bars[1].close
            )

            self._ema += self._alpha * (
                close - self._ema
            )

        current_close = float(
            bars[0].close
        )

        current_ema = self._ema + self._alpha * (
            current_close - self._ema
        )

        return PriceValue(
            float(bars[0].low) - current_ema
        )