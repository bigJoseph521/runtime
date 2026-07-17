from __future__ import annotations

from typing import Final

from alphovex_sdk import (
    ADX,
    EMA,
    MACD,
    IndicatorUpdateMode,
    OrderType,
    Strategy,
    RSI
)
from alphovex_sdk.models import Bar

class AAPLTrendStrategy(Strategy):
    SYMBOL: Final[str] = "AAPL"
    QUANTITY: Final[float] = 1.0

    def on_init(self) -> None:
        # Ticks drive on_tick(). Quotes aren't needed by this strategy.
        self.data.subscribe_symbol(
            symbol=self.SYMBOL,
            ticks=True,
            quotes=False,
            bar_timeframes=("1m", "5m", "15m"),
        )

        # 15m trend indicators.
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

        # 5m strength and momentum indicators.
        self._adx_5m = self.indicator.register(
            indicator=ADX(period=14),
            symbol=self.SYMBOL,
            timeframe="5m",
            update_mode=IndicatorUpdateMode.TICK,
        )

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

        # Previous close-minus-EMA difference used for crossover detection.
        self._previous_1m_difference: float | None = None

        # Prevent repeated orders while a condition remains true.
        # Values: "long", "short", or None.
        self._signal_side: str | None = None

    def on_tick(self) -> None:
        ema_15m_20, _ = self.indicator.get_value(self._ema_15m_20)
        ema_15m_50, _ = self.indicator.get_value(self._ema_15m_50)
        adx_5m_result, _ = self.indicator.get_value(self._adx_5m)
        macd_5m_result, _ = self.indicator.get_value(self._macd_5m)
        ema_1m_20, _ = self.indicator.get_value(self._ema_1m_20)
        rsi_1m, _ = self.indicator.get_value(self._rsi_1m)

        # The runtime normally suppresses on_tick until registered indicators
        # are ready. Keep this guard for additional strategy-level safety.
        if any(
            value is None
            for value in (
                ema_15m_20,
                ema_15m_50,
                adx_5m_result,
                macd_5m_result,
                ema_1m_20,
                rsi_1m,
            )
        ):
            return

        bars_1m = self.data.get_latest_bars(
            symbol=self.SYMBOL,
            timeframe="1m",
            start=0,
            count=1,
        )

        if not bars_1m:
            return

        current_close = float(bars_1m[0].close)

        # ADX returns: (ADX, +DI, -DI)
        adx_value = float(adx_5m_result[0])

        # MACD returns: (MACD, signal, histogram)
        macd_histogram = float(macd_5m_result[2])

        current_difference = current_close - float(ema_1m_20)

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

        # Save it before submitting an order so a submission failure cannot
        # repeatedly interpret the same price transition as a new crossover.
        self._previous_1m_difference = current_difference

        buy_condition = (
            float(ema_15m_20) > float(ema_15m_50)
            and adx_value > 22.0
            and macd_histogram > 0.0
            and crossed_above
            and 52.0 <= float(rsi_1m) <= 72.0
        )

        sell_condition = (
            float(ema_15m_20) < float(ema_15m_50)
            and adx_value > 22.0
            and macd_histogram < 0.0
            and crossed_below
            and 28.0 <= float(rsi_1m) <= 48.0
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
                ema_1m_20=float(ema_1m_20),
                rsi_1m=float(rsi_1m),
                adx_5m=adx_value,
                macd_histogram_5m=macd_histogram,
                ema_15m_20=float(ema_15m_20),
                ema_15m_50=float(ema_15m_50),
            )

        elif sell_condition and self._signal_side != "short":
            self.sell(
                symbol=self.SYMBOL,
                quantity=self.QUANTITY,
                order_type=OrderType.MARKET,
            )
            self._signal_side = "short"

            self.logging.info(
                message="AAPL sell signal submitted",
                close=current_close,
                ema_1m_20=float(ema_1m_20),
                rsi_1m=float(rsi_1m),
                adx_5m=adx_value,
                macd_histogram_5m=macd_histogram,
                ema_15m_20=float(ema_15m_20),
                ema_15m_50=float(ema_15m_50),
            )