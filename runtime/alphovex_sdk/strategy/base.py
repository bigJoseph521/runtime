from __future__ import annotations

from abc import ABC
from typing import Final, final

from ..context import (
    AccountContext,
    DataContext,
    LoggingContext,
    OrderContext,
    ParamsContext,
    StrategyContext,
    TimeContext,
    IndicatorContext,
    PositionContext,
    StorageContext
)

from ..models import (
    MarketEvent
)
from ..errors.strategy import (
    StrategyContextNotFoundError, 
    StrategyNotInitializedError, 
)

from alphovex_sdk.models.order import TimeInForce

__all__: Final[list[str]] = ["Strategy"]


class Strategy(ABC):
    """
    Base class for all user strategies.

    Users should inherit from ``Strategy`` and override lifecycle methods such as
    ``on_init()``, ``on_start()``, ``on_bar()``, ``on_quote()``, ``on_tick()``,
    ``on_order_update()``, ``on_fill()``, ``on_timer()``, and ``on_stop()`` to
    implement trading logic.

    Platform functionality is exposed through read-only properties:

    - ``self.account`` for portfolio, balances, and positions
    - ``self.data`` for market data access
    - ``self.order`` for order submission and order lookup
    - ``self.logging`` for strategy logs
    - ``self.params`` for configured strategy parameters
    - ``self.time`` for current time and time-related utilities

    Notes
    -----
    - ``initialize()`` is managed by the platform and must not be overridden.
    - Users should place one-time setup logic in ``on_init()``.
    - Context-backed properties are provided by the platform and are read-only.
    - Internal methods prefixed with ``_`` are not part of the user-facing API.
    """

    _context: StrategyContext | None
    _initialized: bool

    def __init__(self) -> None:
        """
        Create a new strategy instance.

        Users normally do not need to override ``__init__()``. Strategy setup
        should be done in ``on_init()`` so it runs after the platform binds the
        strategy context.
        """
        self._context = None
        self._initialized = False

    def _bind_context(self, context: StrategyContext) -> None:
        self._context = context

    def _ensure_context_bound(self) -> StrategyContext:
        if self._context is None:
            raise StrategyContextNotFoundError()
        return self._context

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise StrategyNotInitializedError()

    def initialize(self) -> None:
        """
        Perform platform-managed strategy initialization.

        This method is called by the platform before the strategy begins normal
        execution. Users must not override this method.

        What this method does
        ---------------------
        - verifies that a strategy context is already bound
        - prevents duplicate initialization
        - marks the strategy as initialized
        - calls ``on_init()`` for user-defined setup

        Users should put configuration and one-time setup logic in ``on_init()``.
        """
        self._ensure_context_bound()

        if self._initialized:
            return

        self._initialized = True
        self.on_init()

    @property
    def account(self) -> AccountContext:
        """
        Access account information available to the strategy.

        Use this property to inspect balances, portfolio state, and positions.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        AccountContext
            Account-related operations and data visible to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().account

    @property
    def data(self) -> DataContext:
        """
        Access market data available to the strategy.

        Use this property to request historical data or inspect the latest
        market data made available by the platform.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        DataContext
            Market data access available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().data

    @property
    def order(self) -> OrderContext:
        """
        Access order operations available to the strategy.

        Use this property to submit order intents, inspect existing orders,
        and request order cancellation.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        OrderContext
            Order-related operations available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().order

    @property
    def logging(self) -> LoggingContext:
        """
        Access logging facilities available to the strategy.

        Use this property to write debug, informational, warning, and error logs
        that help explain strategy behavior during execution.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        LoggingContext
            Logging utilities available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().logging

    @property
    def params(self) -> ParamsContext:
        """
        Access strategy parameters configured by the platform.

        Use this property to read parameter values supplied for the strategy run.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        ParamsContext
            Parameter access available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().params

    @property
    def time(self) -> TimeContext:
        """
        Access time-related information available to the strategy.

        Use this property to read the current platform time and other
        time-related utilities exposed by the SDK.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        TimeContext
            Time-related utilities available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().time
    
    @property
    def indicator(self) -> IndicatorContext:
        """
        Access indicator operations available to the strategy.

        Use this property to register indicators and get their latest values.

        This property is provided by the platform and is read-only.
        Users must not override or assign to this property.

        Returns
        -------
        IndicatorContext
            Indicator-related operations available to the strategy.
        """
        self._ensure_initialized()
        return self._ensure_context_bound().indicator
    
    @property
    def position(self) -> PositionContext:
        self._ensure_initialized()
        return self._ensure_context_bound().position

    @property
    def storage(self) -> StorageContext:
        self._ensure_initialized()
        return self._ensure_context_bound().storage

    def on_init(self) -> None:
        """
        Perform one-time strategy setup.

        This method is called once by the platform before normal strategy execution begins.

        Use this method to prepare everything the strategy needs before it starts
        receiving ticks, timer callbacks, portfolio updates, or platform events.

        Typical setup work includes:

        - reading and validating strategy parameters
        - initializing internal variables
        - preparing symbol lists, thresholds, or configuration values
        - creating dictionaries or collections used by the strategy
        - setting scheduled timers
        - reading strategy-owned storage
        - registering indicators that will be used during strategy execution

        Indicators that the strategy needs during execution should be registered in 
        this method so the platform can prepare them before they are used.

        Example
        ------
        ```python
            class ValueMomentumStrategy(Strategy):
                def on_init(self) -> None:
                    self.max_spread = self.params.get("max_spread", default=0.5)
                    previous_symbols = self.storage.get(key="selected_symbols", default=[])
                    self.time.set_timer(interval=5)
                    
                    for symbol in previos_symbols:
                        self.indicator.register(
                            indicator=SMA(window_size=20, update_mode=IndicatorUpdateMode.BAR),
                            symbol=symbol,
                            timeframe=Timeframe.M1
                        )
        ```

        Notes
        -----
        This method should be used for setup only.

        It should not contain the main trading decision logic. Market-driven trading logic should
        be implemented in the strategy callback that receives market activity.
        
        It should not contain an infinite loop, sleep logic, or repeated scheduled work.
        Use a scheduled timer for repeated logic.

        If this method is not overridden, the default implementation does nothing.

        Returns
        -------
        None
        """
        ...

    def on_tick(self) -> None:
        """
        Handle a new tick event and implement the main market-driven strategy logic.

        This method is called by the platform when a new tick is delievered to the strategy.

        A tick represents the lastest tick-level market event for a symbol. For most
        strategies, this method is the main place to implement price-driven trading logic,
        such as checking market conditions, reading indicator value, deciding whether to 
        buy or sell, and submitting orders.

        Before this method is called, the platform updates the market data visible through
        SDK contexts. This means strategy code can read the lastest synchronized data from
        contexts such as 'self.data' and 'self.indicator'.

        Use this method to implement logic such as:
        - reading registered indicator values
        - reading the lastest bid and ask price
        - deciding whether to enter or exit a position
        - checking spread before submitting an order
        - submitting buy or sell orders
        - checking whether a bar has completed
        - reacting to the lastest traded place
        - reading the lastest completed bar
        - updating strategy-owned storage


        Example
        -------
        ```python
        class MyStrategy(Strategy):
            SYMBOL = "AAPL"

            def on_tick(self) -> None:
                tick = self.data.get_latest_tick(self.SYMBOL)
                if tick is None:
                    return

                if not self.data.is_new_bar(
                    symbol=self.SYMBOL,
                    timeframe=Timeframe.M1,
                ):
                    return
                bar = self.data.get_latest_bars(
                    symbol=self.SYMBOL,
                    timeframe=Timeframe.M1,
                )[0]

                bid = self.data.best_bid(self.SYMBOL)
                ask = self.data.best_ask(self.SYMBOL)
                
                if bid is None or ask is None:
                    return

                spread = ask - bid

                if spread > 0.05:
                    return
                
                sma = self.indicator.get_indicator_value("sma")

                if sma is not None and bar.close > sma:
                    self.buy(
                        symbol = self.SYMBOL,
                        quantity = 10
                    )

                    self.storage.set(
                        key=f"last_signal/{self.SYMBOL}",
                        value="BUY"
                    )
        ```

        Notes
        -----
        This method should focus on market-driven decision logic.

        It should not manually fetch raw provider data, manage market data subscriptions, 
        or run its own event loop.

        Use SDK contexts to read the lastest market data, account state, portfolio state,
        and indicator values.

        Bar-based logic can be handled inside this method by checking whether a bar has
        completed.

        Returns
        -------
        None
        """
        ...

    def on_portfolio_update(self) -> None:
        """
        Handle portfolio state updates.

        This method is called by the platform after the portfolio state visible to
        the strategy has been updated.

        Use this method to react when portfolio-related information changes, such as 
        positions, open orders, balances, buying power, or other account and
        portfolio values exposed through the SDK.

        Example
        -------
        ```python
        ```

        Notes
        -----
        This method does not recieve an event parameter.
        It should not try to manually update portfolio, order, position, balance,
        or account state. The platform updates those values and exposes the latest
        synchronized state through SDK contexts.

        Strategy code should use this method only to react to the update state.

        Typical Use Cases include:
        - checking updated positions
        - checking updated open orders
        - checking updated buying power
        - preventing duplicate orders
        - updating strategy-owned storage
        - registering or unregistering symbol indicators
        - logging portfolio state changes
        - adjusting strategy behavior after portfolio changes
        
        Returns
        -------
        None
        """

        ...

    def on_timer(self) -> None:
        """
        Handle strategy-defined scheduled timer logic.

        This method is called by the platform at the interval configured for the strategy developer 

        Use this method for logic that should run repeatedly or periodically,
        such as refreshing a symbol universe, rebalancing a portfolio, checking
        strategy conditions, or updating custom state, or writing periodic logs.

        The strategy developer defines the timer interval in on_init() function.
        The platform is responsible for calling this method at the configured time.

        Example
        -------
        ```python
        class ValueMomentumStrategy(Strategy):
            def on_init(self) -> None:
                self.time.set_timer(interval=5)
            def on_timer(self) -> None:
        ```

        Notes
        -----
        Do not implement your own infinite loop, sleep, or scheduler inside this method.
        The platform controls when the timer is triggered

        InCorrect:
        ```python
        def on_timer(self) -> None:
            while True:
                self.refresh_portfolio()
                time.sleep(1000)
        ```

        Correct:
        ```python
        def on_init(self) -> None:
            self.time.set_timer(interval=5m)
        def on_timer(self) -> None:
            self.refresh_portfolio()
        ```
        """
        
        ...

    def on_event(self, event: MarketEvent) -> None:
        """
        Handle a market event delivered by the platform.

        The platform calls this method when a market-session, trading-status,
        or corporate-action event occurs.

        Market events include:

        - pre-market session opening
        - regular market session opening
        - regular market session closing
        - post-market session closing
        - trading halts
        - trading resumptions
        - stock splits and reverse stock splits
        - cash-dividend distributions
        - symbol changes
        - delisting warnings
        - final delistings

        The platform detects and creates these events. Strategy developers
        implement this method only to define how the strategy responds to
        them.

        Parameters
        ----------
        event
            Market event delivered to the strategy.

            Every event contains:

            - ``type``: Type of market event.
            - ``occurred_at``: Time when the event occurred.

            Concrete event classes contain additional fields associated with
            that event. For example:

            - ``TradingHaltedEvent`` contains the halt scope, affected symbol,
            market or venue, halt reason, halt code, and expected resumption
            time.
            - ``SplitEvent`` contains the affected symbol, split ratio, and
            effective time.
            - ``DividendEvent`` contains the affected symbol, dividend amount,
            currency, and relevant dividend dates.

        Examples
        --------
        ```python
        class MyStrategy(Strategy):
            def on_event(self, event: MarketEvent) -> None:
                if event.type is MarketEventType.MARKET_OPEN:
                    self.prepare_for_market_open()

                elif event.type is MarketEventType.MARKET_CLOSE:
                    self.prepare_for_market_close()

                elif isinstance(event, TradingHaltedEvent):
                    if event.scope is TradingHaltScope.SYMBOL:
                        self.handle_symbol_halt(event.symbol)

                elif isinstance(event, SplitEvent):
                    self.handle_split(
                        symbol=event.symbol,
                        quantity_factor=event.quantity_factor,
                        price_factor=event.price_factor,
                    )
        ```

        Notes
        -----
        This method defines the strategy's response to market events. It
        should not detect market events or modify event objects.

        Event-specific information should be read from the concrete event
        object.

        Use ``event.type`` when only the event category is needed. Use
        ``isinstance()`` when accessing fields defined by a concrete event
        class.
        """
        ...


    @final
    def buy(
        self, 
        symbol, 
        quantity, 
        order_type, 
        limit_price = None, 
        stop_price = None, 
        time_in_force = TimeInForce.DAY
    ):
        self.order.buy(
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
    
    @final
    def sell(
        self, 
        symbol, 
        quantity, 
        order_type, 
        limit_price = None, 
        stop_price = None, 
        time_in_force = TimeInForce.DAY
    ):
        self.order.sell(
            symbol=symbol,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force
        )
