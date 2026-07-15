from ...errors import InvalidValueError
from ...models import Bar
from ...typedefs import PriceValue
from ..base import Indicator
from ..helpers import validate_price_type


class Alligator(Indicator):
    """
    Calculate jaw, teeth, and lips.

    Returned tuple order:

    ``jaw, teeth, lips``
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
        periods = (
            jaw_period,
            teeth_period,
            lips_period,
        )

        shifts = (
            jaw_shift,
            teeth_shift,
            lips_shift,
        )

        if min(periods) < 1:
            raise InvalidValueError(
                message="Alligator periods must be greater than 0",
                details={
                    "jaw_period": jaw_period,
                    "teeth_period": teeth_period,
                    "lips_period": lips_period,
                },
            )

        if min(shifts) < 0:
            raise InvalidValueError(
                message="Alligator shifts must be non-negative",
                details={
                    "jaw_shift": jaw_shift,
                    "teeth_shift": teeth_shift,
                    "lips_shift": lips_shift,
                },
            )

        validate_price_type(price_type)

        self._periods = periods
        self._shifts = shifts
        self._price_type = price_type

        self._closed_values: list[float | None] = [
            None,
            None,
            None,
        ]

        self._current_values: list[float | None] = [
            None,
            None,
            None,
        ]

    @property
    def required_history(self) -> int:
        return max(self._periods)

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
            self._closed_values = (
                self._current_values.copy()
            )

        current_price = float(
            bars[0].get_price(self._price_type)
        )

        current_values: list[float | None] = []
        result: list[PriceValue] = []

        for period, closed_value in zip(
            self._periods,
            self._closed_values,
        ):
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
                        bar.get_price(
                            self._price_type
                        )
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