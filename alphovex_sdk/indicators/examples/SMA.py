from __future__ import annotations


from ...typedefs import PriceValue
from ..base import Indicator
from ...errors import InvalidValueError
from ..helpers import validate_price_type
from ...models import Bar

class SMA(Indicator):
    def __init__(
        self,
        period: int,
        price_type: str = "close",
    ) -> None:
        if period < 1:
            raise InvalidValueError(
                message="SMA period must be greater than 0",
                details={"period": period},
            )

        validate_price_type(price_type=price_type)

        self._period = period
        self._price_type = price_type

        self._sum: PriceValue | None = None
        self._oldest_price: PriceValue | None = None
        self._previous_current_price: PriceValue | None = None

    @property
    def required_history(self) -> int:
        return self._period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self._period:
            return None

        current_price = bars[0].get_price(self._price_type)

        if self._sum is None:
            self._sum = sum(
                bar.get_price(self._price_type)
                for bar in bars[:self._period]
            )

        elif is_new_bar:
            if self._oldest_price is None:
                return None

            self._sum += current_price - self._oldest_price

        elif self._previous_current_price is not None:
            self._sum += (
                current_price
                - self._previous_current_price
            )

        self._previous_current_price = current_price
        self._oldest_price = bars[
            self._period - 1
        ].get_price(self._price_type)

        return self._sum / self._period