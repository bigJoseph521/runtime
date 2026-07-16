# Alphovex SDK

`alphovex-sdk` is the public Python SDK used to build trading strategies for the Alphovex runtime.

The runtime owns market-data subscriptions, indicator scheduling, portfolio synchronization, order routing, timers, and persistent strategy storage. Strategy code focuses on lifecycle callbacks and accesses platform services through the contexts exposed by `Strategy`.

## Current package

- Package: `alphovex-sdk`
- Version: `3.0.0`
- Python: `3.11` or newer
- Runtime dependencies: `numpy>=1.24`, `pandas>=2.0`
- Built-in indicators: `SMA`, `EMA`, `MACD`
- Supported timeframes: `"1m"`, `"5m"`, `"15m"`, `"30m"`, `"1h"`, `"1d"`

## Installation

Install the SDK from the project directory containing `pyproject.toml`:

```bash
python -m pip install .
```

For editable development:

```bash
python -m pip install -e .
```

## Quick start

The following example registers a 20-period SMA for one symbol and evaluates the signal when a new one-minute bar starts.

```python
from alphovex_sdk import (
    IndicatorUpdateMode,
    OrderType,
    SMA,
    Strategy,
)


class MovingAverageStrategy(Strategy):
    SYMBOL = "AAPL"
    TIMEFRAME = "1m"

    def on_init(self) -> None:
        period = self.params.get("sma_period", default=20)

        self.sma_handle = self.indicator.register(
            indicator=SMA(period=period, price_type="close"),
            symbol=self.SYMBOL,
            timeframe=self.TIMEFRAME,
            update_mode=IndicatorUpdateMode.BAR,
            history_size=100,
        )

        self.time.set_timer(interval=5)
        self.logging.info(
            "Strategy initialized",
            symbol=self.SYMBOL,
            period=period,
        )

    def on_tick(self) -> None:
        if not self.data.is_new_bar(
            symbol=self.SYMBOL,
            timeframe=self.TIMEFRAME,
        ):
            return

        bars = self.data.get_latest_bars(
            symbol=self.SYMBOL,
            timeframe=self.TIMEFRAME,
            start=0,
            count=1,
        )
        if not bars:
            return

        sma, was_updated = self.indicator.get_value(self.sma_handle)
        if not was_updated or sma is None:
            return

        has_position = bool(
            self.position.get_positions_for_symbol(self.SYMBOL)
        )

        if bars[0].close > sma and not has_position:
            self.buy(
                symbol=self.SYMBOL,
                quantity=1.0,
                order_type=OrderType.MARKET,
            )

    def on_timer(self) -> None:
        self.logging.debug(
            "Periodic strategy check",
            market_open=self.time.is_market_open(self.SYMBOL),
        )
```

The runtime constructs the strategy, binds its contexts, and calls `initialize()`. Strategy implementations must override `on_init()` rather than `initialize()`.

## Strategy lifecycle

A strategy inherits from `alphovex_sdk.Strategy` and may override these callbacks:

| Callback | Purpose |
| --- | --- |
| `on_init()` | One-time setup, parameter reads, indicator registration, and timer configuration. |
| `on_tick()` | Main trade-tick-driven strategy logic. Market data and indicators are synchronized before the callback; read the latest tick through `self.data`. |
| `on_portfolio_update()` | React after the runtime updates account, position, and active-order state. |
| `on_timer()` | Run scheduled logic at the interval configured with `self.time.set_timer(...)`. |
| `on_event(event)` | React to a `MarketEventType`, such as market open, close, halt, or resume. |

Do not create an infinite loop, call `sleep()`, implement a private scheduler, or manually manage market-data subscriptions inside a callback. The runtime owns the event loop.

Indicators can be registered from any strategy callback, not only
`on_init()`. A new registration is warmed immediately from historical bars.
Realtime market-data ingestion continues during that work, but the runtime
does not call `on_tick()` while any active indicator is still warming. Tick
callbacks resume automatically after every registered indicator is ready, so
strategy tick logic does not need to handle partially initialized values.

### Market events

`on_event()` receives a `MarketEventType` enum value:

```python
from alphovex_sdk import MarketEventType, Strategy


class SessionAwareStrategy(Strategy):
    def on_event(self, event: MarketEventType) -> None:
        if event == MarketEventType.MARKET_OPEN:
            self.logging.info("Regular market opened")
        elif event == MarketEventType.MARKET_CLOSE:
            self.logging.info("Regular market closed")
```

Available values are:

- `PRE_MARKET_OPEN`
- `MARKET_OPEN`
- `MARKET_CLOSE`
- `POST_MARKET_CLOSE`
- `TRADING_HALTED`
- `TRADING_RESUMED`

## Strategy contexts

The runtime injects a `StrategyContext`. A strategy accesses each service through a read-only property.

| Property | Context | Main responsibilities |
| --- | --- | --- |
| `self.account` | `AccountContext` | Account balances, equity, margins, and sizing helpers. |
| `self.data` | `DataContext` | Bars, trades, current bars, quotes, daily summaries, and fundamentals. |
| `self.indicator` | `IndicatorContext` | Indicator registration, current values, history, and unregistration. |
| `self.logging` | `LoggingContext` | Structured debug, info, warning, and error logs. |
| `self.order` | `OrderContext` | Buy/sell submission, cancellation, and order queries. |
| `self.params` | `ParamsContext` | Read-only deployment parameters. |
| `self.position` | `PositionContext` | Current position snapshots. |
| `self.storage` | `StorageContext` | Strategy-owned JSON-compatible persistent state. |
| `self.time` | `TimeContext` | Runtime time, date, timers, and market-session state. |

## Market data

### Ordering

Methods returning multiple observations use **newest-to-oldest** ordering:

```python
bars = self.data.get_latest_bars(
    symbol="AAPL",
    timeframe="5m",
    start=0,
    count=20,
)

newest = bars[0]
oldest = bars[-1]
```

`start=0` means the newest available item. `start=1` skips the newest item.

### Bars

```python
bars = self.data.get_latest_bars(
    symbol="AAPL",
    timeframe="1m",
    start=0,
    count=50,
    limit=500,
)

current = self.data.get_current_bar(
    symbol="AAPL",
    timeframe="1m",
)

new_bar_started = self.data.is_new_bar(
    symbol="AAPL",
    timeframe="1m",
)
```

`get_current_bar()` returns the currently forming bar or `None`. `is_new_bar()` reports the runtime event cycle in which the first update for a new timeframe interval is detected; the previous bar is then considered complete.

A `Bar` is immutable and contains:

```text
Bar(
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    ts: datetime,
)
```

The timestamp is the bar opening time. Convenience properties include `is_bullish`, `is_bearish`, `body`, `price_range`, `upper_wick`, `lower_wick`, `mid_price`, `typical_price`, and `weighted_price`.

`Bar.get_price(price_type)` supports:

- `"open"`
- `"high"`
- `"low"`
- `"close"`
- `"typical"`
- `"weighted"`

### Trades

```python
trades = self.data.get_latest_trades(
    symbol="AAPL",
    start=0,
    count=100,
)

latest_trade = self.data.get_latest_trade("AAPL")
```

A `Tick` is immutable and currently contains:

```text
Tick(
    ts: datetime,
    price: float,
    volume: float,
)
```

The current `Tick` model does not contain a symbol field. Strategies should therefore use the symbol associated with their configured runtime stream, registered indicator, or strategy parameter when calling symbol-specific contexts.

### Quotes

```python
quote = self.data.get_latest_quote("AAPL")
bid = self.data.get_best_bid("AAPL")
ask = self.data.get_best_ask("AAPL")
spread = self.data.get_spread("AAPL")
```

`get_latest_quote()` raises `LookupError` when no quote exists. The bid, ask, and spread helpers return `None` when quote data is unavailable.

A `Quote` contains `ts`, `bid_price`, `bid_size`, `ask_price`, and `ask_size`, plus calculated `mid` and `spread` properties.

### Daily summaries

```python
summaries = self.data.get_daily_summaries(
    symbols=["AAPL", "MSFT"],
)

if summaries is not None:
    apple_daily_bar = summaries["AAPL"]
```

Pass `"ALL"` to request every available symbol.

### Fundamentals

Fundamentals are returned as a mapping from factor to a symbol-value mapping:

```python
from alphovex_sdk import FinancialFactor

fundamentals = self.data.get_fundamentals(
    fields=[
        FinancialFactor.PE_RATIO,
        FinancialFactor.MARKET_CAP,
    ],
    symbols=["AAPL", "MSFT"],
)

if fundamentals is not None:
    apple_pe = fundamentals[FinancialFactor.PE_RATIO]["AAPL"]
```

The current `FinancialFactor` values are:

| Member | Provider-neutral value |
| --- | --- |
| `PE_RATIO` | `price_to_earnings` |
| `PB_RATIO` | `price_to_book` |
| `EV_EBITDA` | `ev_to_ebitda` |
| `PRICE_TO_SALES` | `price_to_sales` |
| `PRICE_TO_FREE_CASH_FLOW` | `price_to_free_cash_flow` |
| `ROE` | `return_on_equity` |
| `ROA` | `return_on_assets` |
| `EPS` | `earnings_per_share` |
| `FREE_CASH_FLOW` | `free_cash_flow` |
| `NET_INCOME` | `net_income` |
| `OPERATING_INCOME` | `operating_income` |
| `REVENUE` | `revenue` |
| `EBITDA` | `ebitda` |
| `GROSS_PROFIT` | `gross_profit` |
| `DEBT_TO_EQUITY` | `debt_to_equity` |
| `CURRENT_RATIO` | `current` |
| `QUICK_RATIO` | `quick` |
| `CASH_RATIO` | `cash` |
| `CASH_POSITION` | `cash_and_equivalents` |
| `TOTAL_DEBT` | `total_debt` |
| `MARKET_CAP` | `market_cap` |
| `DIVIDEND_YIELD` | `dividend_yield` |
| `SHARES_OUTSTANDING` | `shares_outstanding` |

Pass `"ALL"` for either `fields` or `symbols` to request all available values.

### Data limits

| Constant | Value |
| --- | ---: |
| `DEFAULT_BAR_LIMIT` | `500` |
| `MAX_BAR_LIMIT` | `5000` |
| `DEFAULT_TRADE_LIMIT` | `500` |
| `MAX_TRADE_LIMIT` | `5000` |

## Indicators

Indicators are registered against a symbol and timeframe. `register()` returns an opaque handle; strategy code must not depend on its internal representation.

```python
from alphovex_sdk import IndicatorUpdateMode, EMA

handle = self.indicator.register(
    indicator=EMA(period=20, price_type="close"),
    symbol="AAPL",
    timeframe="5m",
    update_mode=IndicatorUpdateMode.TICK,
    history_size=200,
)

latest_value, was_updated = self.indicator.get_value(handle)
recent_values = self.indicator.get_values(
    handle,
    start=0,
    count=10,
)
```

`value(handle)` returns `(value, was_updated)`. The Boolean reports whether that indicator was updated during the current runtime event.

`values()` returns stored outputs from newest to oldest.

```python
removed = self.indicator.unregister(handle)
self.indicator.unregister_all()
```

### Update modes

| Mode | Behavior |
| --- | --- |
| `IndicatorUpdateMode.BAR` | Update from completed bars. |
| `IndicatorUpdateMode.TICK` | Update or preview from the current forming bar when trade ticks arrive. |

### Indicator output history

| Constant | Value |
| --- | ---: |
| `DEFAULT_INDICATOR_HISTORY_SIZE` | `100` |
| `MIN_INDICATOR_HISTORY_SIZE` | `1` |
| `MAX_INDICATOR_HISTORY_SIZE` | `1000` |

### Built-in indicators

#### SMA

```python
SMA(period=20, price_type="close")
```

Returns a `float` or `None` until enough bars are available.

#### EMA

```python
EMA(
    period=20,
    price_type="close",
    warmup_period=None,
)
```

The default warm-up is `period * 3`, with a minimum of `period`.

#### MACD

```python
MACD(
    fast_period=12,
    slow_period=26,
    signal_period=9,
    price_type="close",
    warmup_period=None,
)
```

Returns:

```python
{
    "macd": float,
    "signal": float,
    "histogram": float,
}
```

or `None` until the warm-up requirement is satisfied.

### Custom indicators

A custom indicator inherits from `Indicator`, declares `required_history`, and implements `calculate()`.

```python
from typing import Any

from alphovex_sdk import Bar, Indicator


class HighestClose(Indicator):
    def __init__(self, period: int) -> None:
        if period < 1:
            raise ValueError("period must be greater than zero")
        self._period = period

    @property
    def required_history(self) -> int:
        return self._period

    def calculate(
        self,
        bars: list[Bar],
        *,
        is_new_bar: bool,
    ) -> Any | None:
        if len(bars) < self._period:
            return None

        return max(
            bar.close
            for bar in bars[: self._period]
        )
```

The `bars` list is authoritative and is ordered newest to oldest. Do not modify the list or its `Bar` objects.

For BAR registrations, `bars[0]` represents the most recently completed bar. For TICK registrations, `bars[0]` represents the current forming bar followed by completed bars.

An implementation may recalculate from the full window on each call or maintain rolling state. `is_new_bar` allows an optimized implementation to distinguish a new bar from another update to the same forming bar.

## Orders

Submit orders through `self.order` or the `Strategy.buy()` and `Strategy.sell()` convenience methods.

```python
from alphovex_sdk import OrderType, TimeInForce

self.buy(
    symbol="AAPL",
    quantity=10.0,
    order_type=OrderType.LIMIT,
    limit_price=210.00,
    time_in_force=TimeInForce.DAY,
)

self.sell(
    symbol="AAPL",
    quantity=10.0,
    order_type=OrderType.STOP,
    stop_price=198.00,
)
```

Available order types:

- `MARKET`
- `LIMIT`
- `STOP`
- `STOP_LIMIT`
- `TAKE_PROFIT`
- `TRAILING_STOP`

Available time-in-force values:

- `DAY`
- `GTC`
- `IOC`
- `FOK`
- `GTD`
- `AT_THE_OPEN`
- `AT_THE_CLOSE`
- `GOOD_TILL_EXPIRED`
- `GOOD_TILL_TIME`
- `GOOD_TILL_TIME_NANO`

Cancellation and query methods:

```python
cancelled_count = self.order.cancel_all()
cancelled_for_symbol = self.order.cancel_with_symbol("AAPL")
cancel_requested = self.order.cancel_with_id(order_id)

active_orders = self.order.get_all_active_orders()
order = self.order.get_active_order_with_id(order_id)
symbol_orders = self.order.get_active_orders_with_symbol("AAPL")
recent_orders = self.order.get_recent_orders(count=10)
today_count = self.order.get_today_order_count()
```

Order state is platform-owned. Treat returned `Order` objects as snapshots rather than mutating them to simulate execution.

## Positions and account state

### Positions

```python
positions = self.position.get_all_positions()
apple_positions = self.position.get_positions_for_symbol("AAPL")
```

A `Position` includes symbol, quantity, average price, market price, market value, unrealized PnL, timestamp, and optional broker/runtime fields such as instrument ID, cost basis, realized PnL, and side.

### Account

```python
account = self.account.get_account_info()

cash = self.account.cash_balance()
buying_power = self.account.buying_power()
equity = self.account.equity()
available = self.account.available_funds()
```

Risk and sizing helpers:

```python
maintenance_deficit = (
    self.account.has_maintenance_margin_deficit()
)
below_initial_margin = self.account.is_below_initial_margin()
maintenance_buffer = self.account.margin_buffer()
initial_buffer = self.account.initial_margin_buffer()

can_cover = self.account.can_cover_notional(5_000.0)
can_cover_safely = (
    self.account.can_conservatively_cover_notional(5_000.0)
)

max_qty = self.account.max_theoretical_quantity(price=200.0)
safer_max_qty = self.account.max_conservative_quantity(price=200.0)
```

These helpers are simplified prechecks. Passing one does not guarantee broker acceptance and is not a replacement for strategy-level risk management.

## Parameters

Read deployment parameters through `ParamsContext`:

```python
period = self.params.get("period", default=20)
threshold = self.params.get("threshold")

period, threshold = self.params.get_params(
    "period",
    "threshold",
)
```

The context is read-only. Parameter values may be strings, numbers, booleans, lists, dictionaries, or other platform-supported types.

## Timers and sessions

```python
from datetime import date, datetime

now: datetime = self.time.now()
today: date = self.time.today()

self.time.set_timer(interval=5)

session = self.time.current_session("AAPL")
market_open = self.time.is_market_open("AAPL")
```

`set_timer(interval)` currently accepts an integer interval in minutes. The runtime subsequently invokes `on_timer()` at the configured interval.

`MarketSession` provides:

- `contains(timestamp)`
- `is_open`
- `duration_minutes`
- `remaining_minutes`

Session types include pre-market, regular, post-market, extended, after-hours, pre-open, and post-close.

## Strategy storage

`StorageContext` stores small, strategy-owned JSON-compatible values.

```python
count = self.storage.get("entry_count", default=0)
self.storage.set("entry_count", count + 1)

self.storage.set(
    "selected_symbols",
    ["AAPL", "MSFT"],
)

self.storage.set(
    "rebalance_state",
    {
        "last_date": "2026-07-01",
        "enabled": True,
    },
)
```

Supported values are `str`, `int`, `float`, `bool`, `None`, lists, dictionaries, and nested combinations that can be serialized as JSON.

Do not use strategy storage as the source of truth for orders, fills, positions, balances, risk limits, broker account status, or portfolio ledger records. Those values belong to platform-managed contexts.

## Logging

Logging methods support structured keyword context:

```python
self.logging.debug(
    "Checking entry conditions",
    symbol="AAPL",
)

self.logging.info(
    "Submitting order",
    symbol="AAPL",
    quantity=10,
)

self.logging.warning(
    "Spread too wide",
    spread=0.08,
)

self.logging.error(
    "Signal calculation failed",
    indicator="MACD",
)
```

Available methods are `debug()`, `info()`, `warning()`, and `error()`.

## Core models

Most runtime models are immutable dataclasses.

| Model | Main fields |
| --- | --- |
| `Bar` | `open`, `high`, `low`, `close`, `volume`, `ts` |
| `Tick` | `ts`, `price`, `volume` |
| `Quote` | `ts`, `bid_price`, `bid_size`, `ask_price`, `ask_size` |
| `Account` | `broker`, balances, equity, margins, available funds, optional PnL values |
| `Position` | symbol, quantity, average/market prices, market value, PnL, timestamp |
| `OrderIntent` | symbol, side, quantity, price, order type, optional limit/stop/TIF |
| `Order` | intent, ID, status, fill information, message, timestamps |
| `Fill` | order ID, instrument ID, quantity, price, occurrence time |
| `MarketSession` | symbol, session type, status, start/end time, snapshot timestamp |
| `Money` | amount and currency |

Common order status helpers include `Order.is_active`, `Order.is_done`, `Order.remaining_quantity`, `Order.fill_ratio`, and `Order.has_fills`.

## Type aliases

The SDK uses aliases to make public signatures easier to read. They do not create new runtime types.

```python
Symbol = str
InstrumentId = str
Timeframe = Literal["1m", "5m", "15m", "30m", "1h", "1d"]
Timestamp = datetime
TimestampLike = datetime | str
DateLike = date | str
QuantityValue = float
PriceValue = float
CashValue = float
PercentValue = float
OrderId = UUID
```

## Errors

SDK errors inherit from `SDKError` and expose:

- `message`
- `code`
- `details`
- `to_dict()`

Error groups include:

- market-data errors, such as unavailable, stale, incomplete, invalid-range, timeout, and unsupported-timeframe errors;
- order validation, rejection, not-found, finalized, buying-power, and operation errors;
- generic validation errors, such as missing parameters, invalid types or values, invalid state, range violations, unsupported values, and incompatible parameters;
- strategy lifecycle errors, such as missing context or use before initialization.

```python
from alphovex_sdk import SDKError

try:
    self.buy(
        symbol="AAPL",
        quantity=0,
        order_type=OrderType.MARKET,
    )
except SDKError as exc:
    self.logging.error(
        "SDK operation failed",
        error=exc.to_dict(),
    )
```

## Utility functions

The root package exports common helpers for:

- time conversion: `to_datetime`, `to_date`, `now_utc`, `today_utc`, `timeframe_to_timedelta`;
- numeric work: `safe_div`, `is_close`, `clamp`, `normalize`, `to_percent`, `from_percent`, `round_to`, `is_finite`;
- validation: `require_not_none`, `require_type`, `require_positive`, `require_range`, `require_non_empty`, `require_in`, `require_enum`, `normalize_symbol`.

## Package layout

```text
alphovex_sdk/
├── context/      # Runtime service interfaces
├── errors/       # SDK error hierarchy
├── indicators/   # Indicator base class, built-ins, and helpers
├── models/       # Immutable market, order, account, and session models
├── strategy/     # Strategy base class and lifecycle callbacks
├── typedefs/     # Public type aliases
├── utils/        # Numeric, time, and validation utilities
├── __init__.py   # Root public imports
└── pyproject.toml
```

## Current implementation notes

- Strategies are driven primarily through `on_tick()`; there are no `on_bar()` or `on_quote()` callbacks in the current `Strategy` class.
- `on_portfolio_update()` receives no event object. Read the synchronized state from account, order, and position contexts.
- `on_event()` receives a `MarketEventType` enum, not a structured event payload.
- The enabled built-in indicator set is currently limited to `SMA`, `EMA`, and `MACD`.
- Indicator handles are intentionally typed as `Any` and must be treated as opaque runtime values.
- Market-data collections and indicator histories are returned newest first.
