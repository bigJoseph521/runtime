import numpy as np

from alphovex_sdk.strategy.base import Strategy

from alphovex_sdk.indicators.trend import SMA
from alphovex_sdk.context.indicator_context import IndicatorUpdateMode
from alphovex_sdk.models.order import OrderType
from alphovex_sdk.models.market_data import Tick
class SMACrossOver(Strategy):
    def on_init(self):
        symbol_list, ohlcv = self.data.daily_stock_summary("ALL")
        range_array = ohlcv[:, 1] - ohlcv[:, 2]
        candidate_symbol = symbol_list[int(np.argmax(range_array))]

        self._fast_period = self.params.get("fast")
        self._slow_period = self.params.get("slow")
        self._fast_sma_handle = self.indicator.register(
            indicator = SMA(self._fast_period),
            symbol = candidate_symbol,
            timeframe="1m",
            update_mode=IndicatorUpdateMode.TICK
        )
        self._slow_sma_handle = self.indicator.register(
            indicator = SMA(self._slow_period),
            symbol = candidate_symbol,
            timeframe="1m",
            update_mode=IndicatorUpdateMode.TICK
        )
    
    def on_tick(self, tick: Tick):
        self.data.get_latest_bars()
        fast_sma = self.indicator.values(self._fast_sma_handle)
        slow_sma = self.indicator.values(self._slow_sma_handle)

        # market regime detect

        #uptrend
        ###

        #range
        ###

        if fast_sma > slow_sma:
            self.buy(
                symbol="AAPL",
                quantity=1.0,
                order_type= OrderType.MARKET
            )
        else:
            self.sell(
                symbol="AAPL",
                quantity=1.0,
                order_type= OrderType.MARKET
            )
