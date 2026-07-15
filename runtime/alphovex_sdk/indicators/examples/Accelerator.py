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
    ) -> PriceValue | None:
        """Return Awesome Oscillator minus its signal-period SMA.

        Recalculation from the supplied newest-first bar window keeps the
        implementation correct for both forming-bar updates and new bars.
        ``is_new_bar`` is accepted as part of the Indicator contract.
        """
        del is_new_bar

        if len(bars) < self.required_history:
            return None

        prices = [
            float(bar.get_price(self._price_type))
            for bar in bars[: self.required_history]
        ]

        awesome_values: list[float] = []
        for offset in range(self._signal_period):
            fast_average = (
                sum(prices[offset : offset + self._fast_period])
                / self._fast_period
            )
            slow_average = (
                sum(prices[offset : offset + self._slow_period])
                / self._slow_period
            )
            awesome_values.append(fast_average - slow_average)

        signal = sum(awesome_values) / self._signal_period
        return PriceValue(awesome_values[0] - signal)
