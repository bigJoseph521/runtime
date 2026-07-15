from __future__ import annotations

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class CHO(Indicator):
    """
    Calculate the Chaikin Oscillator.

    The oscillator is the difference between the fast and slow
    exponential moving averages of cumulative
    Accumulation/Distribution.

    Bars must be ordered from newest to oldest. Completed state is
    updated only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_slow_period",
        "_fast_alpha",
        "_slow_alpha",
        "_ad",
        "_fast_ema",
        "_slow_ema",
    )

    def __init__(
        self,
        fast_period: int = 3,
        slow_period: int = 10,
    ) -> None:
        if type(fast_period) is not int or fast_period < 1:
            raise InvalidValueError(
                "'fast_period' must be a positive integer"
            )

        if type(slow_period) is not int or slow_period < 1:
            raise InvalidValueError(
                "'slow_period' must be a positive integer"
            )

        if fast_period >= slow_period:
            raise InvalidValueError(
                "'fast_period' must be less than 'slow_period'"
            )

        self._slow_period = slow_period
        self._fast_alpha = 2.0 / (fast_period + 1.0)
        self._slow_alpha = 2.0 / (slow_period + 1.0)

        self._ad: float | None = None
        self._fast_ema: float | None = None
        self._slow_ema: float | None = None

    @property
    def required_history(self) -> int:
        return self._slow_period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        was_uninitialized = self._ad is None

        if was_uninitialized:
            ad = 0.0
            fast_ema = 0.0
            slow_ema = 0.0

            # Initialize from slow_period - 1 completed bars.
            # The current forming bar supplies the final value.
            for index in range(
                self._slow_period - 1,
                0,
                -1,
            ):
                bar = bars[index]
                high = float(bar.high)
                low = float(bar.low)
                price_range = high - low

                if price_range != 0.0:
                    ad += (
                        (
                            2.0 * float(bar.close)
                            - high
                            - low
                        )
                        / price_range
                        * float(bar.volume)
                    )

                if index == self._slow_period - 1:
                    fast_ema = ad
                    slow_ema = ad
                else:
                    fast_ema += self._fast_alpha * (
                        ad - fast_ema
                    )
                    slow_ema += self._slow_alpha * (
                        ad - slow_ema
                    )

            self._ad = ad
            self._fast_ema = fast_ema
            self._slow_ema = slow_ema

        if (
            self._ad is None
            or self._fast_ema is None
            or self._slow_ema is None
        ):
            return None

        # Work with non-optional local values. Besides making the invariant
        # explicit to type checkers, this prevents partially initialized state
        # from ever reaching the arithmetic below.
        ad = self._ad
        fast_ema = self._fast_ema
        slow_ema = self._slow_ema

        if is_new_bar and not was_uninitialized:
            bar = bars[1]
            high = float(bar.high)
            low = float(bar.low)
            price_range = high - low

            if price_range != 0.0:
                ad += (
                    (
                        2.0 * float(bar.close)
                        - high
                        - low
                    )
                    / price_range
                    * float(bar.volume)
                )

            fast_ema += self._fast_alpha * (ad - fast_ema)
            slow_ema += self._slow_alpha * (ad - slow_ema)

            self._ad = ad
            self._fast_ema = fast_ema
            self._slow_ema = slow_ema

        bar = bars[0]
        high = float(bar.high)
        low = float(bar.low)
        price_range = high - low
        current_ad = ad

        if price_range != 0.0:
            current_ad += (
                (
                    2.0 * float(bar.close)
                    - high
                    - low
                )
                / price_range
                * float(bar.volume)
            )

        current_fast_ema = (
            fast_ema
            + self._fast_alpha
            * (current_ad - fast_ema)
        )

        current_slow_ema = (
            slow_ema
            + self._slow_alpha
            * (current_ad - slow_ema)
        )

        return PriceValue(
            current_fast_ema - current_slow_ema
        )
