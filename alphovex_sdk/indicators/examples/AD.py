from __future__ import annotations


from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type
from ...models import Bar

class AD(Indicator):
    """
    Calculate the Accumulation/Distribution line.

    Bar order
    ---------
    bars[0]
        Current forming bar.
    bars[1]
        Most recently completed bar.
    """

    def __init__(self) -> None:
        self._closed_value: PriceValue | None = None

    @property
    def required_history(self) -> int:
        # Keep the current bar and the latest completed bar.
        return 2

    @staticmethod
    def _money_flow_volume(bar: Bar) -> PriceValue:
        price_range = bar.high - bar.low

        if price_range == 0:
            return 0.0

        multiplier = (
            (bar.close - bar.low)
            - (bar.high - bar.close)
        ) / price_range

        return multiplier * bar.volume

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if not bars:
            return None

        if self._closed_value is None:
            # Initialize from available completed bars.
            self._closed_value = sum(
                self._money_flow_volume(bar)
                for bar in reversed(bars[1:])
            )

        elif is_new_bar:
            if len(bars) < 2:
                return None

            # Commit the bar that has just completed.
            self._closed_value += self._money_flow_volume(
                bars[1],
            )

        # Preview the current forming bar without changing closed state.
        return (
            self._closed_value
            + self._money_flow_volume(bars[0])
        )