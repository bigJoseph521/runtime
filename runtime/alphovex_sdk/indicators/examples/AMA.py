from __future__ import annotations

from collections import deque

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class AMA(Indicator):
    """
    Calculate the Adaptive Moving Average.

    Parameters
    ----------
    ama_period
        Number of price changes used for the efficiency ratio.
    fast_ma_period
        Fast smoothing period.
    slow_ma_period
        Retained as an indicator input. It does not contribute to the
        reference calculation.
    shift
        Horizontal display shift. It does not affect calculation.
    price_type
        Source bar price type.

    Notes
    -----
    Bars must be ordered from newest to oldest:

    - ``bars[0]`` is the current forming bar.
    - ``bars[1]`` is the latest completed bar.
    - ``bars[-1]`` is the oldest available bar.

    The first value is seeded from the source price after
    ``ama_period`` bars exist. Full recursive calculation begins when
    one additional bar exists.

    Completed state is committed only when ``is_new_bar`` is ``True``.
    """

    __slots__ = (
        "_ama_period",
        "_price_type",
        "_fast_smoothing_constant",
        "_prices",
        "_value",
    )

    def __init__(
        self,
        ama_period: int = 10,
        fast_ma_period: int = 2,
        slow_ma_period: int = 30,
        shift: int = 0,
        price_type: str = "open",
    ) -> None:
        if (
            not isinstance(ama_period, int)
            or isinstance(ama_period, bool)
            or ama_period < 1
        ):
            raise InvalidValueError(
                "'ama_period' must be a positive integer"
            )

        if (
            not isinstance(fast_ma_period, int)
            or isinstance(fast_ma_period, bool)
            or fast_ma_period < 1
        ):
            raise InvalidValueError(
                "'fast_ma_period' must be a positive integer"
            )

        if (
            not isinstance(slow_ma_period, int)
            or isinstance(slow_ma_period, bool)
            or slow_ma_period < 1
        ):
            raise InvalidValueError(
                "'slow_ma_period' must be a positive integer"
            )

        if fast_ma_period > slow_ma_period:
            raise InvalidValueError(
                "'fast_ma_period' must not be greater than "
                "'slow_ma_period'"
            )

        if not isinstance(shift, int) or isinstance(shift, bool):
            raise InvalidValueError(
                "'shift' must be an integer"
            )

        validate_price_type(price_type)

        self._ama_period = ama_period
        self._price_type = price_type
        self._fast_smoothing_constant = (
            2.0 / (fast_ma_period + 1.0)
        )

        # Completed prices ordered from oldest to newest.
        self._prices: deque[float] = deque(
            maxlen=ama_period,
        )

        # AMA value for the latest committed completed bar.
        self._value: float | None = None

    @property
    def required_history(self) -> int:
        """
        Return the required bar-buffer capacity.
        """
        return self._ama_period + 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        """
        Calculate AMA for the current forming bar.

        Parameters
        ----------
        bars
            Bars ordered from newest to oldest.
        is_new_bar
            ``True`` when ``bars[1]`` has just completed.

        Returns
        -------
        PriceValue | None
            Current AMA value, seed value, or ``None`` when insufficient
            history exists.
        """
        bar_count = len(bars)

        if bar_count < self._ama_period:
            return None

        if (
            bar_count == self._ama_period
            and self._value is None
        ):
            return PriceValue(
                bars[0].get_price(self._price_type)
            )

        if self._value is None:
            self._prices.clear()

            for index in range(
                self._ama_period,
                0,
                -1,
            ):
                self._prices.append(
                    float(
                        bars[index].get_price(
                            self._price_type
                        )
                    )
                )

            # Seed from the latest completed price.
            self._value = self._prices[-1]

        elif is_new_bar:
            completed_price = float(
                bars[1].get_price(self._price_type)
            )

            self._value = self._calculate_next(
                completed_price
            )
            self._prices.append(completed_price)

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        return PriceValue(
            self._calculate_next(current_price)
        )

    def _calculate_next(
        self,
        price: float,
    ) -> float:
        """
        Calculate the next value without changing completed state.
        """
        previous_value = self._value

        if previous_value is None:
            return price

        prices = iter(self._prices)
        oldest_price = next(prices)

        signal = abs(price - oldest_price)
        noise = 0.0
        previous_price = oldest_price

        for current_price in prices:
            noise += abs(
                current_price - previous_price
            )
            previous_price = current_price

        noise += abs(price - previous_price)

        efficiency_ratio = (
            signal / noise
            if noise != 0.0
            else 0.0
        )

        smoothing_constant = (
            efficiency_ratio
            * self._fast_smoothing_constant
        )

        return (
            previous_value
            + smoothing_constant
            * smoothing_constant
            * (price - previous_value)
        )