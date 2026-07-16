from alphovex_sdk import (
    Strategy,
    SMA,
    IndicatorUpdateMode,
    OrderType
)
class SMACrossOver(Strategy):
    def on_init(self):
        self._fast_period = self.params.get("fast")
        self._slow_period = self.params.get("slow")
        self._fast_sma_handle = self.indicator.register(
            indicator = SMA(self._fast_period),
            symbol = "AAPL",
            timeframe="1m",
            update_mode=IndicatorUpdateMode.TICK
        )
        self._slow_sma_handle = self.indicator.register(
            indicator = SMA(self._slow_period),
            symbol = "AAPL",
            timeframe="5m",
            update_mode=IndicatorUpdateMode.TICK
        )
    
    def on_tick(self):
        fast_sma, _ = self.indicator.get_value(self._fast_sma_handle)
        slow_sma, _ = self.indicator.get_value(self._slow_sma_handle)

        if fast_sma is None or slow_sma is None:
            return

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
