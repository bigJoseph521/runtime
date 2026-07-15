from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class ASI(Indicator):
    """
    Calculate the Accumulation Swing Index.

    Bars must be ordered from newest to oldest. Completed state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_maximum_price_change",
        "_previous_bar",
        "_value",
    )

    def __init__(
        self,
        t: float = 300.0,
        point: float = 0.0001,
    ) -> None:
        if (
            not isinstance(t, (int, float))
            or isinstance(t, bool)
            or t <= 0.0
        ):
            raise InvalidValueError(
                "'t' must be greater than zero"
            )

        if (
            not isinstance(point, (int, float))
            or isinstance(point, bool)
            or point <= 0.0
        ):
            raise InvalidValueError(
                "'point' must be greater than zero"
            )

        self._maximum_price_change = float(t) * float(point)
        self._previous_bar: Bar | None = None
        self._value: float = 0.0

    @property
    def required_history(self) -> int:
        return 2

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < 2:
            return None

        if self._previous_bar is None:
            self._previous_bar = bars[1]

        elif is_new_bar:
            self._value = self._next_value(bars[1])
            self._previous_bar = bars[1]

        return PriceValue(
            self._next_value(bars[0])
        )

    def _next_value(
        self,
        bar: Bar,
    ) -> float:
        previous_bar = self._previous_bar

        if previous_bar is None:
            return self._value

        previous_open = float(previous_bar.open)
        previous_close = float(previous_bar.close)

        current_open = float(bar.open)
        current_high = float(bar.high)
        current_low = float(bar.low)
        current_close = float(bar.close)

        high_change = abs(current_high - previous_close)
        low_change = abs(current_low - previous_close)
        price_range = current_high - current_low
        movement = max(high_change, low_change)

        if high_change >= low_change and high_change >= price_range:
            denominator = (
                high_change
                - 0.5 * low_change
                + 0.25
                * abs(previous_close - previous_open)
            )
        elif low_change >= high_change and low_change >= price_range:
            denominator = (
                low_change
                - 0.5 * high_change
                + 0.25
                * abs(previous_close - previous_open)
            )
        else:
            denominator = (
                price_range
                + 0.25
                * abs(previous_close - previous_open)
            )

        if denominator == 0.0:
            return self._value

        weighted_change = (
            current_close
            - previous_close
            + 0.5 * (current_close - current_open)
            + 0.25 * (previous_close - previous_open)
        )

        swing_index = (
            50.0
            * weighted_change
            * movement
            / self._maximum_price_change
            / denominator
        )

        return self._value + swing_index