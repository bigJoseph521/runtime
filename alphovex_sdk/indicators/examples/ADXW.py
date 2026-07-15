from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class ADXW(Indicator):
    """
    Calculate ADX, positive DI, and negative DI using Wilder smoothing.

    Returned tuple order:

    ``adx, plus_di, minus_di``
    """

    def __init__(
        self,
        period: int = 14,
    ) -> None:
        if period < 1:
            raise InvalidValueError(
                message="ADXW period must be greater than 0",
                details={"period": period},
            )

        self._period = period

        # ATR, smoothed +DM, smoothed -DM, ADX.
        self._closed_state: tuple[
            PriceValue,
            PriceValue,
            PriceValue,
            PriceValue,
        ] = (0.0, 0.0, 0.0, 0.0)

        self._initialized = False

    @property
    def required_history(self) -> int:
        return max(3, self._period + 1)

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

        if not self._initialized:
            state = self._closed_state

            # Process completed bars from oldest to newest without
            # creating a reversed copy of the bar list.
            for index in range(
                len(bars) - self._period - 1,
                0,
                -1,
            ):
                (
                    atr,
                    plus_dm,
                    minus_dm,
                    adx,
                    _,
                    _,
                ) = self._step(
                    current=bars[index],
                    previous=bars[index + 1],
                    state=state,
                )

                state = (
                    atr,
                    plus_dm,
                    minus_dm,
                    adx,
                )

            self._closed_state = state
            self._initialized = True

        elif is_new_bar:
            (
                atr,
                plus_dm,
                minus_dm,
                adx,
                _,
                _,
            ) = self._step(
                current=bars[1],
                previous=bars[2],
                state=self._closed_state,
            )

            self._closed_state = (
                atr,
                plus_dm,
                minus_dm,
                adx,
            )

        (
            _,
            _,
            _,
            adx,
            plus_di,
            minus_di,
        ) = self._step(
            current=bars[0],
            previous=bars[1],
            state=self._closed_state,
        )

        return (
            PriceValue(adx),
            PriceValue(plus_di),
            PriceValue(minus_di),
        )

    def _step(
        self,
        current: Bar,
        previous: Bar,
        state: tuple[
            PriceValue,
            PriceValue,
            PriceValue,
            PriceValue,
        ],
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
        PriceValue,
        PriceValue,
        PriceValue,
    ]:
        atr, plus_dm, minus_dm, adx = state

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

        atr = (
            atr * (self._period - 1)
            + true_range
        ) / self._period

        plus_dm = (
            plus_dm * (self._period - 1)
            + up_move
        ) / self._period

        minus_dm = (
            minus_dm * (self._period - 1)
            + down_move
        ) / self._period

        if atr == 0.0:
            plus_di = 0.0
            minus_di = 0.0
        else:
            plus_di = 100.0 * plus_dm / atr
            minus_di = 100.0 * minus_dm / atr

        total_di = plus_di + minus_di

        dx = (
            100.0
            * abs(plus_di - minus_di)
            / total_di
            if total_di != 0.0
            else 0.0
        )

        adx = (
            adx * (self._period - 1)
            + dx
        ) / self._period

        return (
            PriceValue(atr),
            PriceValue(plus_dm),
            PriceValue(minus_dm),
            PriceValue(adx),
            PriceValue(plus_di),
            PriceValue(minus_di),
        )