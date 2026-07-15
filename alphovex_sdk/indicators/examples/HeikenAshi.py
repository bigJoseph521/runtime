from __future__ import annotations

from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator


class HeikenAshi(Indicator):
    """
    Calculate Heiken Ashi candles.

    Returned tuple order:

    ``open, high, low, close``

    The Heiken Ashi close is the average of the current bar's open,
    high, low, and close.

    The Heiken Ashi open is the average of the previous completed
    Heiken Ashi open and close.

    For the first available bar, the Heiken Ashi open is seeded using
    the average of that bar's open and close.

    Recursive state is committed only when a new forming bar starts.

    Bars must be ordered from newest to oldest.
    """

    __slots__ = (
        "_committed_open",
        "_committed_close",
        "_forming_open",
        "_forming_close",
    )

    def __init__(self) -> None:
        self._committed_open: PriceValue | None = None
        self._committed_close: PriceValue | None = None

        self._forming_open: PriceValue | None = None
        self._forming_close: PriceValue | None = None

    @property
    def required_history(self) -> int:
        return 1

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue,
        PriceValue,
        PriceValue,
        PriceValue,
    ] | None:
        if not bars:
            return None

        if (
            self._committed_open is None
            and self._committed_close is None
            and len(bars) > 1
        ):
            oldest = bars[-1]

            previous_open = (
                float(oldest.open) + float(oldest.close)
            ) / 2.0

            previous_close = (
                float(oldest.open)
                + float(oldest.high)
                + float(oldest.low)
                + float(oldest.close)
            ) / 4.0

            for index in range(len(bars) - 2, 0, -1):
                bar = bars[index]

                current_close = (
                    float(bar.open)
                    + float(bar.high)
                    + float(bar.low)
                    + float(bar.close)
                ) / 4.0

                current_open = (
                    previous_open + previous_close
                ) / 2.0

                previous_open = current_open
                previous_close = current_close

            self._committed_open = previous_open
            self._committed_close = previous_close

        elif (
            is_new_bar
            and self._forming_open is not None
            and self._forming_close is not None
        ):
            self._committed_open = self._forming_open
            self._committed_close = self._forming_close

        bar = bars[0]

        raw_open = float(bar.open)
        raw_high = float(bar.high)
        raw_low = float(bar.low)
        raw_close = float(bar.close)

        heiken_close = (
            raw_open
            + raw_high
            + raw_low
            + raw_close
        ) / 4.0

        if (
            self._committed_open is None
            or self._committed_close is None
        ):
            heiken_open = (
                raw_open + raw_close
            ) / 2.0
        else:
            heiken_open = (
                float(self._committed_open)
                + float(self._committed_close)
            ) / 2.0

        heiken_high = max(
            raw_high,
            heiken_open,
            heiken_close,
        )

        heiken_low = min(
            raw_low,
            heiken_open,
            heiken_close,
        )

        self._forming_open = PriceValue(heiken_open)
        self._forming_close = PriceValue(heiken_close)

        return (
            self._forming_open,
            PriceValue(heiken_high),
            PriceValue(heiken_low),
            self._forming_close,
        )