from __future__ import annotations


from ...typedefs import PriceValue
from ..base import Indicator
from ...errors import InvalidValueError
from ..helpers import validate_price_type
from ...models import Bar


class EMA(Indicator):
    def __init__(
        self,
        period: int,
        price_type: str = "close",
        *,
        warmup_period: int | None = None,
    ) -> None:
        if period < 1:
            raise InvalidValueError(
                message="EMA period must be greater than 0",
                details={"period": period},
            )

        if warmup_period is not None and warmup_period < 1:
            raise InvalidValueError(
                message="EMA warmup_period must be greater than 0",
                details={"warmup_period": warmup_period},
            )

        validate_price_type(price_type=price_type)

        self._period = period
        self._price_type = price_type
        self._alpha = 2.0 / (period + 1.0)

        self._warmup_period = max(
            period,
            warmup_period if warmup_period is not None else period,
        )

        self._closed_ema: PriceValue | None = None

    @property
    def required_history(self) -> int:
        return self._warmup_period

    def calculate(
        self,
        bars: list[Bar],
        is_new_bar: bool,
    ) -> PriceValue | None:
        if len(bars) < self.required_history:
            return None

        current_price = bars[0].get_price(self._price_type)

        if self._period == 1:
            return current_price

        if self._closed_ema is None:
            completed_bars = bars[1:self.required_history]

            closed_ema = completed_bars[-1].get_price(
                self._price_type,
            )

            for bar in reversed(completed_bars[:-1]):
                price = bar.get_price(self._price_type)

                closed_ema = (
                    self._alpha * price
                    + (1.0 - self._alpha) * closed_ema
                )

            self._closed_ema = closed_ema

        elif is_new_bar:
            closed_price = bars[1].get_price(self._price_type)

            self._closed_ema = (
                self._alpha * closed_price
                + (1.0 - self._alpha) * self._closed_ema
            )

        return (
            self._alpha * current_price
            + (1.0 - self._alpha) * self._closed_ema
        )