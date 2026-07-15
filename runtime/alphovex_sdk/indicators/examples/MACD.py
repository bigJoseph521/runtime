from __future__ import annotations

from collections import deque

from ...typedefs import PriceValue
from ..base import Indicator
from ...errors import InvalidValueError
from ..helpers import validate_price_type
from ...models import Bar

class MACD(Indicator):
    """
    Calculate the Moving Average Convergence/Divergence indicator.

    Calculation
    -----------
    macd
        Fast EMA minus slow EMA.

    signal
        Simple moving average of recent MACD values.

    histogram
        MACD minus signal.

    Expected bar order
    ------------------
    bars[0]
        Current forming bar.

    bars[1]
        Most recently completed bar.

    bars[-1]
        Oldest available bar.

    Notes
    -----
    Internal state contains completed bars only.

    The current forming bar is evaluated as a preview without modifying
    the completed-bar state.
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

        # The signal calculation includes the current forming MACD value,
        # so only signal_period - 1 completed values must be retained.
        self._completed_macd_values: deque[PriceValue] = deque(
            maxlen=max(0, signal_period - 1),
        )

        self._bar_count = 0
        self._initialized = False

    @property
    def required_history(self) -> int:
        """
        Return the number of unique bars required before values are ready.
        """
        return self._warmup_period

    @staticmethod
    def _next_ema(
        value: PriceValue,
        previous: PriceValue,
        alpha: float,
    ) -> PriceValue:
        """
        Calculate the next exponential moving average value.
        """
        return (
            alpha * value
            + (1.0 - alpha) * previous
        )

    def _commit_completed_price(
        self,
        price: PriceValue,
    ) -> None:
        """
        Commit one completed price to the indicator state.
        """
        if self._fast_ema is None or self._slow_ema is None:
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

            completed_macd = (
                self._fast_ema
                - self._slow_ema
            )

        self._completed_macd_values.append(
            completed_macd,
        )

    def _initialize_state(
        self,
        bars: list[Bar],
    ) -> None:
        """
        Initialize the indicator from available completed bars.

        Completed bars are processed from oldest to newest.
        """
        completed_bars = bars[1:]

        for bar in reversed(completed_bars):
            self._commit_completed_price(
                price=bar.get_price(self._price_type),
            )

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
        """
        Calculate the current MACD values.

        Parameters
        ----------
        bars
            Bars ordered from newest to oldest. ``bars[0]`` is the current
            forming bar and ``bars[1]`` is the latest completed bar.

        is_new_bar
            ``True`` exactly once when a new forming bar starts and
            ``bars[1]`` has just completed.

        Returns
        -------
        tuple[PriceValue, PriceValue, PriceValue] | None
            MACD, signal, and histogram values.

            Returns ``None`` until sufficient history is available.
        """
        if not bars:
            return None

        if not self._initialized:
            self._initialize_state(
                bars=bars,
            )

        elif is_new_bar:
            if len(bars) < 2:
                return None

            self._commit_completed_price(
                price=bars[1].get_price(self._price_type),
            )

            self._bar_count += 1

        current_price = bars[0].get_price(
            self._price_type,
        )

        if self._fast_ema is None or self._slow_ema is None:
            fast = current_price
            slow = current_price
        else:
            # Preview the current forming bar without changing state.
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

        signal = (
            sum(self._completed_macd_values)
            + macd
        ) / self._signal_period

        histogram = macd - signal

        return macd, signal, histogram