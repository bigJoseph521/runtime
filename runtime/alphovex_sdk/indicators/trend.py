from __future__ import annotations

from collections import deque

from alphovex_sdk.errors import InvalidValueError
from alphovex_sdk.indicators.base import Indicator
from alphovex_sdk.indicators.helpers import validate_price_type
from alphovex_sdk.models import Bar
from alphovex_sdk.typedefs.aliases import PriceValue
from alphovex_sdk.utils import safe_div

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
        elif is_new_bar and self._oldest_price is not None:
            self._sum += current_price - self._oldest_price
        elif self._previous_current_price is not None:
            self._sum += current_price - self._previous_current_price

        self._previous_current_price = current_price
        self._oldest_price = bars[
            self._period - 1
        ].get_price(self._price_type)

        return self._sum / self._period

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

        validate_price_type(price_type=price_type)

        self._period = period
        self._price_type = price_type
        self._alpha = 2.0 / (period + 1.0)

        self._warmup_period = max(
            period,
            warmup_period if warmup_period is not None else period * 3,
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
        if len(bars) < self._warmup_period:
            return None

        current_price = bars[0].get_price(self._price_type)

        if self._period == 1:
            return current_price

        closed_ema = self._closed_ema

        if closed_ema is None:
            # Initialize using completed bars from oldest to newest.
            for bar in reversed(bars[1:self._warmup_period]):
                price = bar.get_price(self._price_type)

                if closed_ema is None:
                    closed_ema = price
                else:
                    closed_ema = (
                        self._alpha * price
                        + (1.0 - self._alpha) * closed_ema
                    )

            self._closed_ema = closed_ema

        elif is_new_bar:
            # bars[1] is the bar that has just completed.
            closed_price = bars[1].get_price(self._price_type)

            closed_ema = (
                self._alpha * closed_price
                + (1.0 - self._alpha) * closed_ema
            )
            self._closed_ema = closed_ema

        if closed_ema is None:
            return None

        # Calculate the forming-bar EMA without changing closed state.
        return (
            self._alpha * current_price
            + (1.0 - self._alpha) * closed_ema
        )

class MACD(Indicator):
    """
    MACD compatible with the supplied MQL5 implementation.

    Calculation
    -----------
    macd
        Fast EMA minus slow EMA.

    signal
        Simple moving average of the latest MACD values.

    histogram
        MACD minus signal.

    Bar order
    ---------
    bars[0]
        Current forming bar.

    bars[1]
        Most recently completed bar.

    bars[-1]
        Oldest available bar.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        price_type: str = "close",
        *,
        warmup_period: int | None = None,
    ) -> None:
        if fast_period < 1:
            raise InvalidValueError(
                message="MACD fast_period must be greater than 0",
                details={"fast_period": fast_period},
            )

        if slow_period < 1:
            raise InvalidValueError(
                message="MACD slow_period must be greater than 0",
                details={"slow_period": slow_period},
            )

        if signal_period < 1:
            raise InvalidValueError(
                message="MACD signal_period must be greater than 0",
                details={"signal_period": signal_period},
            )

        if fast_period >= slow_period:
            raise InvalidValueError(
                message="MACD fast_period must be less than slow_period",
                details={
                    "fast_period": fast_period,
                    "slow_period": slow_period,
                },
            )

        if warmup_period is not None and warmup_period < 1:
            raise InvalidValueError(
                message="MACD warmup_period must be greater than 0",
                details={"warmup_period": warmup_period},
            )

        validate_price_type(price_type=price_type)

        self._fast_period = fast_period
        self._slow_period = slow_period
        self._signal_period = signal_period
        self._price_type = price_type

        self._fast_alpha = 2.0 / (fast_period + 1.0)
        self._slow_alpha = 2.0 / (slow_period + 1.0)

        # The supplied MQL5 implementation becomes ready when enough MACD
        # values exist for the signal SMA. It does not wait for
        # slow_period + signal_period bars.
        self._warmup_period = max(
            signal_period,
            (
                warmup_period
                if warmup_period is not None
                else signal_period
            ),
        )

        # EMA state based only on completed bars.
        self._fast_ema: PriceValue | None = None
        self._slow_ema: PriceValue | None = None

        # Keep the MACD values of the latest completed bars.
        #
        # The current forming MACD is added temporarily when calculating
        # the signal line.
        self._completed_macd_values: deque[PriceValue] = deque(
            maxlen=max(0, signal_period - 1),
        )

        self._bar_count = 0
        self._initialized = False

    @property
    def required_history(self) -> int:
        """
        Return the number of unique bars required before MACD is ready.
        """
        return self._warmup_period

    @staticmethod
    def _next_ema(
        value: PriceValue,
        previous: PriceValue,
        alpha: float,
    ) -> PriceValue:
        return (
            alpha * value
            + (1.0 - alpha) * previous
        )

    def _commit_completed_price(
        self,
        price: PriceValue,
    ) -> None:
        """
        Commit one completed price to the EMA and MACD state.
        """
        if self._fast_ema is None or self._slow_ema is None:
            # Match the MQL5 EMA initialization: seed with the first price.
            self._fast_ema = price
            self._slow_ema = price

            completed_macd: PriceValue = 0.0
        else:
            self._fast_ema = self._next_ema(
                value=price,
                previous=self._fast_ema,
                alpha=self._fast_alpha,
            )

            self._slow_ema = self._next_ema(
                value=price,
                previous=self._slow_ema,
                alpha=self._slow_alpha,
            )

            completed_macd = self._fast_ema - self._slow_ema

        self._completed_macd_values.append(completed_macd)

    def _initialize_state(
        self,
        bars: list[Bar],
    ) -> None:
        """
        Initialize state from available completed bars.

        Input bars are newest first, so completed bars are processed from
        oldest to newest.
        """
        completed_bars = bars[1:]

        for bar in reversed(completed_bars):
            price = bar.get_price(self._price_type)
            self._commit_completed_price(price=price)

        # Count completed bars plus the current forming bar.
        self._bar_count = len(completed_bars) + 1
        self._initialized = True

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

        if not self._initialized:
            # This supports both:
            #
            # 1. calculation beginning with only one forming bar
            # 2. calculation beginning with historical bars already loaded
            self._initialize_state(bars=bars)

        elif is_new_bar:
            if len(bars) < 2:
                return None

            # bars[1] is the bar that has just completed.
            closed_price = bars[1].get_price(self._price_type)

            self._commit_completed_price(
                price=closed_price,
            )

            self._bar_count += 1

        current_price = bars[0].get_price(self._price_type)

        if self._fast_ema is None or self._slow_ema is None:
            # The first forming bar seeds both EMAs with the same price.
            fast = current_price
            slow = current_price
        else:
            # Preview the current forming bar without changing completed
            # EMA state.
            fast = self._next_ema(
                value=current_price,
                previous=self._fast_ema,
                alpha=self._fast_alpha,
            )

            slow = self._next_ema(
                value=current_price,
                previous=self._slow_ema,
                alpha=self._slow_alpha,
            )

        macd = fast - slow

        if self._bar_count < self._warmup_period:
            return None

        if (
            len(self._completed_macd_values) + 1
            < self._signal_period
        ):
            return None

        # Match SimpleMAOnBuffer:
        #
        # current MACD + previous signal_period - 1 completed MACD values.
        signal = (
            sum(self._completed_macd_values)
            + macd
        ) / self._signal_period

        histogram = macd - signal

        return macd, signal, histogram
