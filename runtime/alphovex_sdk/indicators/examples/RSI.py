from __future__ import annotations

from ..base import Indicator
from ...models import Bar

class RSI(Indicator):
    """
    Calculate RSI from the most recent bars.

    Bars supplied by the runtime are ordered newest to oldest.
    """

    def __init__(
        self,
        period: int = 14,
        price_type: str = "close",
    ) -> None:
        if period < 1:
            raise ValueError("RSI period must be greater than zero")

        self._period = period
        self._price_type = price_type

    @property
    def required_history(self) -> int:
        # RSI(14) needs 15 prices to calculate 14 changes.
        return self._period + 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> float | None:
        del is_new_bar

        if len(bars) < self.required_history:
            return None

        # Runtime bars are newest -> oldest. Reverse the calculation window.
        prices = [
            bar.get_price(self._price_type)
            for bar in reversed(bars[: self.required_history])
        ]

        gains = 0.0
        losses = 0.0

        for previous, current in zip(prices, prices[1:]):
            change = current - previous

            if change > 0.0:
                gains += change
            elif change < 0.0:
                losses -= change

        average_gain = gains / self._period
        average_loss = losses / self._period

        if average_loss == 0.0:
            return 100.0 if average_gain > 0.0 else 50.0

        relative_strength = average_gain / average_loss
        return 100.0 - (100.0 / (1.0 + relative_strength))