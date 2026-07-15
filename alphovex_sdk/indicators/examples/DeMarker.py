from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class DeMarker(Indicator):
    """
    Calculate the DeMarker oscillator.

    For each bar:

    - DeMax is the positive increase from the previous high.
    - DeMin is the positive decrease from the previous low.

    The returned value is:

    ``sum(DeMax) / (sum(DeMax) + sum(DeMin))``

    Bars must be ordered from newest to oldest.
    """

    __slots__ = ("_period",)

    def __init__(
        self,
        period: int = 14,
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        self._period = period

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

        de_max = 0.0
        de_min = 0.0

        for index in range(self._period - 1):
            current_bar = bars[index]
            previous_bar = bars[index + 1]

            high_change = (
                float(current_bar.high)
                - float(previous_bar.high)
            )

            if high_change > 0.0:
                de_max += high_change

            low_change = (
                float(previous_bar.low)
                - float(current_bar.low)
            )

            if low_change > 0.0:
                de_min += low_change

        denominator = de_max + de_min

        if denominator == 0.0:
            return PriceValue(0.0)

        return PriceValue(
            de_max / denominator
        )