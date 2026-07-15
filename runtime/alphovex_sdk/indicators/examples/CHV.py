from __future__ import annotations

from collections import deque

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class CHV(Indicator):
    """
    Calculate Chaikin Volatility.

    CHV is the percentage change between the current EMA of the
    high-low range and the EMA value ``period`` bars earlier.

    Bars must be ordered from newest to oldest. Completed EMA state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_period",
        "_alpha",
        "_ema",
        "_ema_values",
    )

    def __init__(
        self,
        period: int = 10,
    ) -> None:
        if type(period) is not int or period < 2:
            raise InvalidValueError(
                "'period' must be an integer greater than 1"
            )

        self._period = period
        self._alpha = 2.0 / (period + 1.0)

        # EMA for the latest committed completed bar.
        self._ema: float | None = None

        # Latest period completed EMA values, oldest to newest.
        self._ema_values: deque[float] = deque(
            maxlen=period,
        )

    @property
    def required_history(self) -> int:
        return self._period * 2 - 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        if self._ema is None:
            for index in range(
                self.required_history - 1,
                0,
                -1,
            ):
                bar = bars[index]
                price_range = (
                    float(bar.high)
                    - float(bar.low)
                )

                if self._ema is None:
                    self._ema = price_range
                else:
                    self._ema += self._alpha * (
                        price_range - self._ema
                    )

                self._ema_values.append(self._ema)

        elif is_new_bar:
            if self._ema is None:
                return None

            bar = bars[1]
            price_range = (
                float(bar.high)
                - float(bar.low)
            )

            self._ema += self._alpha * (
                price_range - self._ema
            )

            self._ema_values.append(self._ema)

        if self._ema is None or not self._ema_values:
            return None

        bar = bars[0]
        current_range = (
            float(bar.high)
            - float(bar.low)
        )

        current_ema = self._ema + self._alpha * (
            current_range - self._ema
        )

        previous_ema = self._ema_values[0]

        if previous_ema == 0.0:
            return PriceValue(0.0)

        return PriceValue(
            100.0
            * (current_ema - previous_ema)
            / previous_ema
        )
