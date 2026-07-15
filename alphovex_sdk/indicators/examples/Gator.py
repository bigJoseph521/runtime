from __future__ import annotations

from collections import deque

from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class Gator(Indicator):
    """
    Calculate the Gator Oscillator.

    Returned tuple order:

    ``upper, lower``

    The upper histogram is the absolute difference between the Jaw
    and Teeth lines after applying their relative shift.

    The lower histogram is the negative absolute difference between
    the Teeth and Lips lines after applying their relative shift.

    Each output warms up independently.
    """

    def __init__(
        self,
        jaw_period: int = 13,
        jaw_shift: int = 8,
        teeth_period: int = 8,
        teeth_shift: int = 5,
        lips_period: int = 5,
        lips_shift: int = 3,
        price_type: str = "median",
    ) -> None:
        for period in (
            jaw_period,
            teeth_period,
            lips_period,
        ):
            if type(period) is not int or period <= 0:
                raise InvalidValueError(
                    "periods must be positive integers"
                )

        for shift in (
            jaw_shift,
            teeth_shift,
            lips_shift,
        ):
            if type(shift) is not int or shift < 0:
                raise InvalidValueError(
                    "shifts must be non-negative integers"
                )

        if jaw_shift < teeth_shift:
            raise InvalidValueError(
                "jaw_shift must be greater than or equal to teeth_shift"
            )

        if teeth_shift < lips_shift:
            raise InvalidValueError(
                "teeth_shift must be greater than or equal to lips_shift"
            )

        validate_price_type(price_type)

        self._periods = (
            jaw_period,
            teeth_period,
            lips_period,
        )
        self._price_type = price_type

        self._upper_shift = jaw_shift - teeth_shift
        self._lower_shift = teeth_shift - lips_shift

        self._upper_history_required = (
            self._upper_shift
            + teeth_shift
            + teeth_period
            + 1
        )
        self._lower_history_required = (
            self._lower_shift
            + lips_shift
            + lips_period
            + 1
        )

        self._committed_values: list[
            PriceValue | None
        ] = [
            None,
            None,
            None,
        ]

        self._forming_values: list[
            PriceValue | None
        ] = [
            None,
            None,
            None,
        ]

        self._jaw_history: deque[PriceValue] = deque(
            maxlen=max(self._upper_shift, 1),
        )
        self._teeth_history: deque[PriceValue] = deque(
            maxlen=max(self._lower_shift, 1),
        )

    @property
    def required_history(self) -> int:
        return max(
            self._upper_history_required,
            self._lower_history_required,
        )

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> tuple[
        PriceValue | None,
        PriceValue | None,
    ]:
        if not bars:
            return None, None

        if is_new_bar:
            jaw = self._forming_values[0]
            teeth = self._forming_values[1]

            if jaw is not None:
                self._jaw_history.appendleft(jaw)

            if teeth is not None:
                self._teeth_history.appendleft(teeth)

            for index, value in enumerate(
                self._forming_values
            ):
                if value is not None:
                    self._committed_values[index] = value

        current_price = bars[0].get_price(
            self._price_type
        )

        for index, period in enumerate(self._periods):
            previous_value = self._committed_values[index]

            if previous_value is None:
                if len(bars) < period:
                    self._forming_values[index] = None
                    continue

                total = 0.0

                for bar_index in range(period):
                    total += bars[bar_index].get_price(
                        self._price_type
                    )

                self._forming_values[index] = total / period
            else:
                self._forming_values[index] = (
                    previous_value * (period - 1)
                    + current_price
                ) / period

        current_jaw = self._forming_values[0]
        current_teeth = self._forming_values[1]
        current_lips = self._forming_values[2]

        if self._upper_shift == 0:
            shifted_jaw = current_jaw
        elif len(self._jaw_history) >= self._upper_shift:
            shifted_jaw = self._jaw_history[
                self._upper_shift - 1
            ]
        else:
            shifted_jaw = None

        if self._lower_shift == 0:
            shifted_teeth = current_teeth
        elif len(self._teeth_history) >= self._lower_shift:
            shifted_teeth = self._teeth_history[
                self._lower_shift - 1
            ]
        else:
            shifted_teeth = None

        upper: PriceValue | None = None
        lower: PriceValue | None = None

        if (
            len(bars) >= self._upper_history_required
            and shifted_jaw is not None
            and current_teeth is not None
        ):
            upper = abs(
                shifted_jaw - current_teeth
            )

        if (
            len(bars) >= self._lower_history_required
            and shifted_teeth is not None
            and current_lips is not None
        ):
            lower = -abs(
                shifted_teeth - current_lips
            )

        return upper, lower