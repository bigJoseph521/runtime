from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class Envelopes(Indicator):
    """
    Calculate moving-average Envelopes.

    Returned tuple order:

    ``upper, lower``

    Bars must be ordered from newest to oldest.
    """

    __slots__ = (
        "_period",
        "_deviation",
        "_price_type",
    )

    def __init__(
        self,
        period: int = 14,
        deviation: float = 0.1,
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
        self._deviation = float(deviation) / 100.0
        self._price_type = price_type

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
    ] | None:
        if len(bars) < self.required_history:
            return None

        total = 0.0

        for index in range(self._period):
            total += float(
                bars[index].get_price(self._price_type)
            )

        average = total / self._period
        distance = average * self._deviation

        return (
            PriceValue(average + distance),
            PriceValue(average - distance),
        )