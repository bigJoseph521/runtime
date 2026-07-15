from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class ForceIndex(Indicator):
    """
    Calculate the Force Index using a simple moving average.

    Force Index is calculated as:

    ``volume * (current_sma - previous_sma)``

    Bars must be ordered from newest to oldest.
    """

    __slots__ = ("_period",)

    def __init__(
        self,
        period: int = 13,
    ) -> None:
        if type(period) is not int or period < 1:
            raise InvalidValueError(
                "'period' must be a positive integer"
            )

        self._period = period

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

        ma_change = (
            float(bars[0].close)
            - float(bars[self._period].close)
        ) / self._period

        return PriceValue(
            float(bars[0].volume) * ma_change
        )