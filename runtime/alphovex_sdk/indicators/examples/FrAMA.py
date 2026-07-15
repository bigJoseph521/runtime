from __future__ import annotations

from math import exp, log

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class FrAMA(Indicator):
    """
    Calculate the Fractal Adaptive Moving Average.

    ``period`` is the length of each half-window. The complete fractal
    dimension window therefore contains ``2 * period`` bars.

    The recursive value is committed only when a new forming bar starts.
    """

    def __init__(
        self,
        period: int = 14,
        shift: int = 0,
        price_type: str = "close",
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "period must be a positive integer"
            )

        if type(shift) is not int:
            raise InvalidValueError(
                "shift must be an integer"
            )

        validate_price_type(price_type=price_type)

        self._period = period
        self._price_type = price_type
        self._committed_value: PriceValue | None = None
        self._forming_value: PriceValue | None = None

    @property
    def required_history(self) -> int:
        return 2 * self._period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if is_new_bar and self._forming_value is not None:
            self._committed_value = self._forming_value

        if len(bars) < self.required_history:
            return None

        period = self._period

        high_1 = bars[0].high
        low_1 = bars[0].low

        for index in range(1, period):
            bar = bars[index]
            high_1 = max(high_1, bar.high)
            low_1 = min(low_1, bar.low)

        high_2 = bars[period].high
        low_2 = bars[period].low

        for index in range(period + 1, 2 * period):
            bar = bars[index]
            high_2 = max(high_2, bar.high)
            low_2 = min(low_2, bar.low)

        high_3 = max(high_1, high_2)
        low_3 = min(low_1, low_2)

        n1 = (high_1 - low_1) / period
        n2 = (high_2 - low_2) / period
        n3 = (high_3 - low_3) / (2 * period)

        if n1 + n2 > 0.0 and n3 > 0.0:
            dimension = (
                log(n1 + n2) - log(n3)
            ) / log(2.0)

            alpha = exp(
                -4.6 * (dimension - 1.0)
            )
        else:
            alpha = 1.0

        previous_value = self._committed_value

        if previous_value is None:
            previous_value = bars[1].get_price(
                self._price_type
            )

        current_price = bars[0].get_price(
            self._price_type
        )

        self._forming_value = (
            alpha * current_price
            + (1.0 - alpha) * previous_value
        )

        return self._forming_value