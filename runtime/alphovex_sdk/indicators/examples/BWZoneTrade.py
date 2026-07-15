from __future__ import annotations

from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class BWZoneTrade(Indicator):
    """
    Calculate the Bill Williams trading zone.

    Returned values:

    - ``0.0``: green zone
    - ``1.0``: red zone
    - ``2.0``: gray zone

    The zone is green when both AO and AC are rising, red when both
    are falling, and gray otherwise.

    Bars must be ordered from newest to oldest.
    """

    __slots__ = ()

    @property
    def required_history(self) -> int:
        return 39

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        # AO values for the current bar and five previous bars.
        ao = [0.0] * 6

        for offset in range(6):
            fast_total = 0.0
            slow_total = 0.0

            for index in range(
                offset + 33,
                offset - 1,
                -1,
            ):
                price = float(
                    bars[index].get_price("median")
                )

                slow_total += price

                if index < offset + 5:
                    fast_total += price

            ao[offset] = (
                fast_total / 5.0
                - slow_total / 34.0
            )

        current_ac = ao[0] - (
            ao[4]
            + ao[3]
            + ao[2]
            + ao[1]
            + ao[0]
        ) / 5.0

        previous_ac = ao[1] - (
            ao[5]
            + ao[4]
            + ao[3]
            + ao[2]
            + ao[1]
        ) / 5.0

        if ao[0] > ao[1] and current_ac > previous_ac:
            return PriceValue(0.0)

        if ao[0] < ao[1] and current_ac < previous_ac:
            return PriceValue(1.0)

        return PriceValue(2.0)