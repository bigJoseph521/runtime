from __future__ import annotations

from typing import Final, cast

from alphovex_sdk import (
    ADX,
    EMA,
    MACD,
    RSI,
    IndicatorUpdateMode,
    OrderType,
    Strategy,
)


class AAPLTrendStrategy(Strategy):
    SYMBOL: Final[str] = "AAPL"
    QUANTITY: Final[float] = 1.0

    def on_init(self) -> None:
        self.data.subscribe_symbol(
            symbol=self.SYMBOL,
            ticks=True,
            quotes=False,
            bar_timeframes=("1m", "5m", "15m"),
        )

        # 15m trend direction.
        self._ema_15m_20 = self.indicator.register(
            indicator=EMA(period=20),
            symbol=self.SYMBOL,
            timeframe="15m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        self._ema_15m_50 = self.indicator.register(
            indicator=EMA(period=50),
            symbol=self.SYMBOL,
            timeframe="15m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        # 5m trend strength.
        self._adx_5m = self.indicator.register(
            indicator=ADX(period=14),
            symbol=self.SYMBOL,
            timeframe="5m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        # 5m momentum.
        self._macd_5m = self.indicator.register(
            indicator=MACD(
                fast_period=12,
                slow_period=26,
                signal_period=9,
            ),
            symbol=self.SYMBOL,
            timeframe="5m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        # 1m entry indicators.
        self._ema_1m_20 = self.indicator.register(
            indicator=EMA(period=20),
            symbol=self.SYMBOL,
            timeframe="1m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        self._rsi_1m = self.indicator.register(
            indicator=RSI(period=14),
            symbol=self.SYMBOL,
            timeframe="1m",
            update_mode=IndicatorUpdateMode.TICK,
        )

        # Previous 1m close-minus-EMA difference for crossover detection.
        self._previous_1m_difference: float | None = None

        # Prevent duplicate orders while the same directional signal remains.
        self._signal_side: str | None = None

    def on_tick(self) -> None:
        ema_15m_20, _ = self.indicator.get_value(
            self._ema_15m_20
        )
        ema_15m_50, _ = self.indicator.get_value(
            self._ema_15m_50
        )
        adx_5m_result, _ = self.indicator.get_value(
            self._adx_5m
        )
        macd_5m_result, _ = self.indicator.get_value(
            self._macd_5m
        )
        ema_1m_20, _ = self.indicator.get_value(
            self._ema_1m_20
        )
        rsi_1m, _ = self.indicator.get_value(
            self._rsi_1m
        )

        # Explicit checks allow mypy to narrow every result.
        if ema_15m_20 is None:
            return
        if ema_15m_50 is None:
            return
        if adx_5m_result is None:
            return
        if macd_5m_result is None:
            return
        if ema_1m_20 is None:
            return
        if rsi_1m is None:
            return

        ema_15m_20_value = float(ema_15m_20)
        ema_15m_50_value = float(ema_15m_50)
        ema_1m_20_value = float(ema_1m_20)
        rsi_1m_value = float(rsi_1m)

        # ADX result: ADX, +DI, -DI.
        adx_values = cast(
            tuple[float, float, float],
            adx_5m_result,
        )

        # MACD result: MACD, signal, histogram.
        macd_values = cast(
            tuple[float, float, float],
            macd_5m_result,
        )

        adx_value = float(adx_values[0])
        macd_histogram = float(macd_values[2])

        bars_1m = self.data.get_latest_bars(
            symbol=self.SYMBOL,
            timeframe="1m",
            start=0,
            count=1,
        )

        # The runtime returns None until current 1m data is available.
        if bars_1m is None:
            return

        current_close = float(bars_1m[0].close)
        current_difference = (
            current_close - ema_1m_20_value
        )

        # A previous observation is required to detect a crossover.
        if self._previous_1m_difference is None:
            self._previous_1m_difference = current_difference
            return

        crossed_above = (
            self._previous_1m_difference <= 0.0
            and current_difference > 0.0
        )

        crossed_below = (
            self._previous_1m_difference >= 0.0
            and current_difference < 0.0
        )

        self._previous_1m_difference = current_difference

        buy_condition = (
            ema_15m_20_value > ema_15m_50_value
            and adx_value > 22.0
            and macd_histogram > 0.0
            and crossed_above
            and 52.0 <= rsi_1m_value <= 72.0
        )

        sell_condition = (
            ema_15m_20_value < ema_15m_50_value
            and adx_value > 22.0
            and macd_histogram < 0.0
            and crossed_below
            and 28.0 <= rsi_1m_value <= 48.0
        )

        if buy_condition and self._signal_side != "long":
            self.buy(
                symbol=self.SYMBOL,
                quantity=self.QUANTITY,
                order_type=OrderType.MARKET,
            )

            self._signal_side = "long"

            self.logging.info(
                message="AAPL buy signal submitted",
                close=current_close,
                ema_1m_20=ema_1m_20_value,
                rsi_1m=rsi_1m_value,
                adx_5m=adx_value,
                macd_histogram_5m=macd_histogram,
                ema_15m_20=ema_15m_20_value,
                ema_15m_50=ema_15m_50_value,
            )

        elif (
            sell_condition
            and self._signal_side != "short"
        ):
            self.sell(
                symbol=self.SYMBOL,
                quantity=self.QUANTITY,
                order_type=OrderType.MARKET,
            )

            self._signal_side = "short"

            self.logging.info(
                message="AAPL sell signal submitted",
                close=current_close,
                ema_1m_20=ema_1m_20_value,
                rsi_1m=rsi_1m_value,
                adx_5m=adx_value,
                macd_histogram_5m=macd_histogram,
                ema_15m_20=ema_15m_20_value,
                ema_15m_50=ema_15m_50_value,
            )