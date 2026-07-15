from __future__ import annotations

from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class Fractals(Indicator):
    """
    Calculate the latest confirmed upper and lower Fractals.

    Returned tuple order:

    ``latest_confirmed_upper, latest_confirmed_lower``

    A fractal candidate is evaluated at ``bars[3]``.

    ``bars[1]`` and ``bars[2]`` are the two newer completed bars.
    ``bars[4]`` and ``bars[5]`` are the two older completed bars.

    Each confirmed value is retained independently until a newer
    corresponding fractal is confirmed.

    Bars must be ordered from newest to oldest.
    """

    __slots__ = (
        "_started",
        "_latest_confirmed_upper",
        "_latest_confirmed_lower",
    )

    def __init__(self) -> None:
        self._started = False

        self._latest_confirmed_upper: PriceValue | None = None
        self._latest_confirmed_lower: PriceValue | None = None

    @property
    def required_history(self) -> int:
        return 6

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue | None,
        PriceValue | None,
    ] | None:
        initialize = not self._started

        if initialize:
            self._started = True

        if len(bars) < self.required_history:
            return None

        if initialize or is_new_bar:
            center = bars[3]

            center_high = float(center.high)
            center_low = float(center.low)

            if (
                center_high > float(bars[1].high)
                and center_high > float(bars[2].high)
                and center_high >= float(bars[4].high)
                and center_high >= float(bars[5].high)
            ):
                self._latest_confirmed_upper = center_high

            if (
                center_low < float(bars[1].low)
                and center_low < float(bars[2].low)
                and center_low <= float(bars[4].low)
                and center_low <= float(bars[5].low)
            ):
                self._latest_confirmed_lower = center_low

        return (
            self._latest_confirmed_upper,
            self._latest_confirmed_lower,
        )