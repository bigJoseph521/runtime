from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class Accelerator(Indicator):
    """
    Calculate the Accelerator Oscillator.

    ``accelerator = awesome - SMA(awesome, signal_period)``
    """

    def __init__(
        self,
        fast_period: int = 5,
        slow_period: int = 34,
        signal_period: int = 5,
        price_type: str = "median",
    ) -> None:
        if min(fast_period, slow_period, signal_period) < 1:
            raise InvalidValueError(
                message="Accelerator periods must be greater than 0",
                details={
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                    "signal_period": signal_period,
                },
            )

        if fast_period >= slow_period:
            raise InvalidValueError(
                message="fast_period must be less than slow_period",
                details={
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                },
            )

        validate_price_type(price_type)

        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
        self._price_type = price_type

    @property
    def required_history(self) -> int:
        return self._slow_period + self._signal_period - 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
    ] | None:
        if not bars:
            return None

        if is_new_bar:
            self._closed_values = self._current_values.copy()

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        current_values: list[PriceValue | None] = []
        result: list[PriceValue] = []

        for index, period in enumerate(self._periods):
            closed_value = self._closed_values[index]

            if closed_value is not None:
                value = (
                    closed_value * (period - 1)
                    + current_price
                ) / period

                current_values.append(value)
                result.append(PriceValue(value))

            elif len(bars) >= period:
                value = sum(
                    float(
                        bar.get_price(self._price_type)
                    )
                    for bar in bars[:period]
                ) / period

                current_values.append(value)
                result.append(PriceValue(value))

            else:
                current_values.append(None)
                result.append(PriceValue(0.0))

        self._current_values = current_values

        return (
            result[0],
            result[1],
            result[2],
        )