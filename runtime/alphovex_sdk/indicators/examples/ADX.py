from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class ADX(Indicator):
    """
    Calculate ADX, positive DI, and negative DI.

    Returned tuple order:

    ``adx, plus_di, minus_di``
    """

    def __init__(
        self,
        period: int = 14,
    ) -> None:
        if period < 1:
            raise InvalidValueError(
                message="ADX period must be greater than 0",
                details={"period": period},
            )

        self._period = period
        self._alpha = 2.0 / (period + 1.0)

        self._closed_values: tuple[
            PriceValue,
            PriceValue,
            PriceValue,
        ] = (0.0, 0.0, 0.0)

        self._last_closed_bar: Bar | None = None

    @property
    def required_history(self) -> int:
        return max(2, self._period)

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
    ] | None:
        if len(bars) < self.required_history:
            return None

        if self._last_closed_bar is None:
            completed_bars = list(reversed(bars[1:]))

            values: tuple[
                PriceValue,
                PriceValue,
                PriceValue,
            ] = (0.0, 0.0, 0.0)

            for previous, current in zip(
                completed_bars,
                completed_bars[1:],
            ):
                values = self._step(
                    current=current,
                    previous=previous,
                    values=values,
                )

            self._closed_values = values
            self._last_closed_bar = completed_bars[-1]

        elif is_new_bar:
            self._closed_values = self._step(
                current=bars[1],
                previous=self._last_closed_bar,
                values=self._closed_values,
            )

            self._last_closed_bar = bars[1]

        return self._step(
            current=bars[0],
            previous=bars[1],
            values=self._closed_values,
        )

    def _step(
        self,
        current: Bar,
        previous: Bar,
        values: tuple[
            PriceValue,
            PriceValue,
            PriceValue,
        ],
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
    ]:
        adx, plus_di, minus_di = values

        up_move = max(
            float(current.high) - float(previous.high),
            0.0,
        )

        down_move = max(
            float(previous.low) - float(current.low),
            0.0,
        )

        if up_move > down_move:
            down_move = 0.0
        elif down_move > up_move:
            up_move = 0.0
        else:
            up_move = 0.0
            down_move = 0.0

        true_range = max(
            float(current.high) - float(current.low),
            abs(
                float(current.high)
                - float(previous.close)
            ),
            abs(
                float(current.low)
                - float(previous.close)
            ),
        )

        if true_range == 0.0:
            raw_plus_di = 0.0
            raw_minus_di = 0.0
        else:
            raw_plus_di = (
                100.0 * up_move / true_range
            )

            raw_minus_di = (
                100.0 * down_move / true_range
            )

        plus_di += self._alpha * (
            raw_plus_di - plus_di
        )

        minus_di += self._alpha * (
            raw_minus_di - minus_di
        )

        total = plus_di + minus_di

        dx = (
            100.0
            * abs(plus_di - minus_di)
            / total
            if total != 0.0
            else 0.0
        )

        adx += self._alpha * (
            dx - adx
        )

        return (
            PriceValue(adx),
            PriceValue(plus_di),
            PriceValue(minus_di),
        )