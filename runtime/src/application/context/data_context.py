from __future__ import annotations

from typing import Any
from collections.abc import Mapping
import asyncio
from datetime import datetime, timedelta, timezone
import numpy as np
import math
import threading
from functools import wraps

from alphovex_sdk import(
    DataContext,
    MAX_BAR_LIMIT,
    MAX_TICK_LIMIT,
    DEFAULT_BAR_LIMIT,
    DEFAULT_TICK_LIMIT,
    Bar,
    Tick,
    Quote,
    FinancialFactor,
    Timeframe,
    InvalidValueError
)

from contracts.rows import (
    _BarRow,
    _TickRow,
    _QuoteRow,
)

from application.event_handling.internal_event_bus import InternalEventBus, InternalEventType
from application.context.logging_context import RuntimeLoggingContext
from application.context.data_model import BarRingBuffer, TickRingBuffer
from application.symbol_reference.symbol_reference import (
    SymbolCheckReason,
    SymbolCheckResult,
    SymbolReferenceService
)
from application.status_managing.manager import StatusManager, Status
from application.ports.historical_data import HistoricalDataClientPort
from infrastructure.storage.client import StorageClient


def _synchronized_market_data(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._data_lock:
            return method(self, *args, **kwargs)

    return wrapper


class RuntimeDataContext(DataContext):
    """
    Single Source of Truth all all runtime trading data

    Contains:
    - Market data(Numpy, high-frequency)
    - Snapshot data
    - Fundamental Data
    - Reference data
    - Selector Data

    Rule: Only strategy worker runtime can mutate this
    Strategy code is read-only    
    """

    def __init__(
        self, 
        storage_client: StorageClient ,
        logger: RuntimeLoggingContext,
        event_bus: InternalEventBus,
        symbol_reference_service: SymbolReferenceService,
        status_manager: StatusManager,
        hds_client: HistoricalDataClientPort
    ):
        self._bar_buffer_size = MAX_BAR_LIMIT
        self._tick_buffer_size = MAX_TICK_LIMIT
        self._data_lock = threading.RLock()
        self._event_loop = asyncio.get_running_loop()

        self._bars : dict[tuple[str, str], BarRingBuffer] = {}
        self._ticks : dict[str, TickRingBuffer] = {}
        self._quotes: dict[str, _QuoteRow] = {}
        self._index_bars: dict[str, _BarRow] = {}
        self._index_values: dict[str, float] = {}
        self._symbol_subscriptions: dict[str, dict[str, Any]] = {}
        self._index_subscriptions: set[str] = set()
        self._is_new_bar: dict[tuple[str, Timeframe], bool] = {}
        self._warmup_seeded: set[tuple[str, Timeframe]] = set()
        self._unavailable_data_logged: set[
            tuple[str, str, str | None]
        ] = set()

        self._storage_client = storage_client
        self._logger = logger
        self._event_bus = event_bus
        self._symbol_reference_service = symbol_reference_service
        self._status_manager = status_manager
        self._hds_client = hds_client

    def _submit_coroutine(self, coroutine) -> None:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self._event_loop:
            self._event_loop.create_task(coroutine)
        else:
            asyncio.run_coroutine_threadsafe(coroutine, self._event_loop)

    #--------------------
    # Internal Helpers
    #--------------------

    def _get_bar_buffer(self, symbol: str, tf:str) -> BarRingBuffer | None:
        key = (symbol, tf)
        if key not in self._bars:
            self._bars[key] = BarRingBuffer(self._bar_buffer_size)
        return self._bars[key]    

    def _get_tick_buffer(self, symbol:str) -> TickRingBuffer:
        return self._ticks.setdefault(
            symbol,
            TickRingBuffer(self._tick_buffer_size)
        )
    
    def _reverse_new(self, arr: np.ndarray) -> np.ndarray:
        """
        Convert oldest-newest into newest-oldest view.
        """
        return arr[::-1]
    
    def _to_float_or_none(
        self,
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        try:
            x = float(value)
        except (TypeError, ValueError):
            return None

        if math.isnan(x) or math.isinf(x):
            return None

        return x

    def _log_data_unavailable_once(
        self,
        *,
        data_type: str,
        symbol: str,
        timeframe: str | None = None,
    ) -> None:
        key = (data_type, symbol, timeframe)
        if key in self._unavailable_data_logged:
            return

        self._unavailable_data_logged.add(key)
        fields: dict[str, Any] = {
            "data_type": data_type,
            "symbol": symbol,
        }
        if timeframe is not None:
            fields["timeframe"] = timeframe

        self._logger.warning(
            message="Requested market data is not available yet",
            **fields,
        )
        self._logger.platform_warning(
            message="Subscribed market-data stream has no current value",
            reason="market_data_not_available",
            **fields,
        )

    def _mark_data_available(
        self,
        *,
        data_type: str,
        symbol: str,
        timeframe: str | None = None,
    ) -> None:
        self._unavailable_data_logged.discard(
            (data_type, symbol, timeframe)
        )

    #--------------------
    # Runtime Functions
    #--------------------

    @_synchronized_market_data
    def update_bars(self, symbol:str, tf: str, bar:_BarRow, is_new: bool):
        buf = self._get_bar_buffer(symbol, tf)

        key = (symbol, tf)

        self._is_new_bar[key] = is_new

        if is_new:
            buf.append(bar=bar)
        else:
            buf.update_current_bar(bar=bar)


    @_synchronized_market_data
    def update_warmup_bar(
        self,
        symbol: str,
        timeframe: Timeframe,
        bar: _BarRow,
        completed: bool,
    ) -> None:
        """Seed a target once; later dynamic registrations do not duplicate it."""
        target = (symbol, timeframe)
        if target in self._warmup_seeded:
            return
        self.update_bars(symbol, timeframe, bar, completed)

    async def complete_warmup_seed(
        self,
        symbol: str,
        timeframe: Timeframe,
        _: int,
    ) -> None:
        with self._data_lock:
            self._warmup_seeded.add((symbol, timeframe))

    @_synchronized_market_data
    def update_ticks(self, symbol: str, tick:_TickRow):
        buf = self._get_tick_buffer(symbol)

        buf.append(tick=tick)


    #--------------------------
    # SDK Functions
    #--------------------------

    @property
    @_synchronized_market_data
    def symbol_subscriptions(self) -> dict[str, dict[str, Any]]:
        return {
            symbol: {
                "ticks": subscription["ticks"],
                "quotes": subscription["quotes"],
                "bar_timeframes": tuple(subscription["bar_timeframes"]),
            }
            for symbol, subscription in self._symbol_subscriptions.items()
        }

    @property
    @_synchronized_market_data
    def index_subscriptions(self) -> frozenset[str]:
        return frozenset(self._index_subscriptions)

    @_synchronized_market_data
    def subscribe_symbol(
        self,
        symbol: str,
        *,
        ticks: bool = True,
        quotes: bool = True,
        bar_timeframes: tuple[str, ...] = ("1m",),
    ) -> None:
        self._validate_symbol(symbol)
        normalized_symbol = symbol.strip().upper()
        supported = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
        normalized_timeframes = tuple(
            dict.fromkeys(str(timeframe).strip().lower() for timeframe in bar_timeframes)
        )
        unsupported = set(normalized_timeframes) - supported
        if unsupported:
            raise InvalidValueError(
                message=f"Unsupported bar timeframe(s): {sorted(unsupported)}"
            )
        if not ticks and not quotes and not normalized_timeframes:
            raise InvalidValueError(message="At least one symbol data type is required")
        self._symbol_subscriptions[normalized_symbol] = {
            "ticks": bool(ticks),
            "quotes": bool(quotes),
            "bar_timeframes": normalized_timeframes,
        }

    @_synchronized_market_data
    def subscribe_index(self, index: str) -> None:
        normalized_index = str(index).strip().upper()
        if not normalized_index:
            raise InvalidValueError(message="Index is required")
        self._index_subscriptions.add(normalized_index)

    @_synchronized_market_data
    def update_index_bar(self, index: str, bar: _BarRow) -> None:
        self._index_bars[index] = bar

    @_synchronized_market_data
    def update_index_value(self, index: str, value: float) -> None:
        self._index_values[index] = value

    @_synchronized_market_data
    def get_latest_index(self, index: str) -> tuple[Bar, float] | None:
        normalized_index = str(index).strip().upper()
        if normalized_index not in self._index_subscriptions:
            raise LookupError(f"Index {normalized_index} was not subscribed in on_init()")
        row = self._index_bars.get(normalized_index)
        value = self._index_values.get(normalized_index)
        if row is None or value is None:
            self._log_data_unavailable_once(
                data_type="index",
                symbol=normalized_index,
            )
            return None

        self._mark_data_available(data_type="index", symbol=normalized_index)
        bar = Bar(
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
            ts=row.ts.astype("datetime64[ms]").tolist(),
        )
        return bar, float(value)
    
    @_synchronized_market_data
    def get_latest_bars(self, symbol, timeframe, *, start, count, limit = None):
        self._validate_symbol(symbol)
        normalized_symbol = str(symbol).strip().upper()
        normalized_timeframe = str(timeframe).strip().lower()
        subscription = self._symbol_subscriptions.get(normalized_symbol)
        if (
            subscription is None
            or normalized_timeframe not in subscription["bar_timeframes"]
        ):
            raise LookupError(
                f"{normalized_symbol} {normalized_timeframe} bars were not "
                "subscribed in on_init()"
            )

        buf = self._get_bar_buffer(
            symbol=normalized_symbol,
            tf=normalized_timeframe,
        )
        # Historical seeding is asynchronous and is owned by WarmUpService.
        # This SDK-facing method remains synchronous and reads the seeded/live
        # ring buffer only.
        

        if buf.size == 0 or start >= buf.size:
            self._log_data_unavailable_once(
                data_type="bar",
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
            )
            return None

        ts = buf.view("ts")
        open_ = buf.view("open")
        high = buf.view("high")
        low = buf.view("low")
        close = buf.view("close")
        volume = buf.view("volume")

        end = min(start + count, buf.size)

        ts = ts[start:end]
        open_ = open_[start:end]
        high = high[start:end]
        low = low[start:end]
        close = close[start:end]
        volume = volume[start:end]
        
        self._mark_data_available(
            data_type="bar",
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
        )
        return tuple(
            Bar(
                open = float(open_[i]),
                high = float(high[i]),
                low = float(low[i]),
                close = float(close[i]),
                volume = float(volume[i]),
                ts=ts[i].astype("datetime64[ms]").tolist(),
            )
            for i in range(ts.shape[0])
        )

    @_synchronized_market_data
    def get_latest_ticks(self, symbol, *, start, count, limit = None):
        self._validate_symbol(symbol)
        normalized_symbol = str(symbol).strip().upper()
        subscription = self._symbol_subscriptions.get(normalized_symbol)
        if subscription is None or not subscription["ticks"]:
            raise LookupError(
                f"{normalized_symbol} ticks were not subscribed in on_init()"
            )

        buf = self._get_tick_buffer(normalized_symbol)
        if buf.size == 0 or start >= buf.size:
            self._log_data_unavailable_once(
                data_type="tick",
                symbol=normalized_symbol,
            )
            return None

        ts = buf.view("ts")
        price = buf.view("price")
        volume = buf.view("volume")

        end = min(start + count, buf.size)

        ts = ts[start:end]
        price = price[start:end]
        volume = volume[start:end]

        self._mark_data_available(
            data_type="tick",
            symbol=normalized_symbol,
        )
        return tuple(
            Tick(
                ts=ts[i].astype("datetime64[ms]").tolist(),
                price= float(price[i]),
                volume= float(volume[i]) 
            )
            for i in range(ts.shape[0])
        )

    @_synchronized_market_data
    def get_current_bar(self, symbol:str, tf:str) -> Bar | None:
        self._validate_symbol(symbol)
        normalized_symbol = str(symbol).strip().upper()
        normalized_timeframe = str(tf).strip().lower()
        subscription = self._symbol_subscriptions.get(normalized_symbol)
        if (
            subscription is None
            or normalized_timeframe not in subscription["bar_timeframes"]
        ):
            raise LookupError(
                f"{normalized_symbol} {normalized_timeframe} bars were not "
                "subscribed in on_init()"
            )

        buf = self._get_bar_buffer(normalized_symbol, normalized_timeframe)

        if buf.size == 0:
            self._log_data_unavailable_once(
                data_type="bar",
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
            )
            return None
        
        i = (buf.head - 1) % buf.capacity

        self._mark_data_available(
            data_type="bar",
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
        )
        return Bar(
            ts=buf.ts[i].astype("datetime64[ms]").tolist(),
            open=float(buf.open[i]),
            high=float(buf.high[i]),
            low=float(buf.low[i]),
            close=float(buf.close[i]),
            volume=float(buf.volume[i]),
        )

    @_synchronized_market_data
    def get_latest_tick(self, symbol: str) -> Tick | None:
        self._validate_symbol(symbol)
        normalized_symbol = str(symbol).strip().upper()
        subscription = self._symbol_subscriptions.get(normalized_symbol)
        if subscription is None or not subscription["ticks"]:
            raise LookupError(
                f"{normalized_symbol} ticks were not subscribed in on_init()"
            )
        buf = self._get_tick_buffer(symbol=normalized_symbol)
        
        if buf.size == 0:
            self._log_data_unavailable_once(
                data_type="tick",
                symbol=normalized_symbol,
            )
            return None
        
        i = (buf.head - 1) % buf.capacity

        self._mark_data_available(data_type="tick", symbol=normalized_symbol)
        return Tick(
            ts=buf.ts[i].astype("datetime64[ms]").tolist(),
            price=float(buf.price[i]),
            volume=float(buf.volume[i]),
        )

    @_synchronized_market_data
    def is_new_bar(self, symbol, timeframe) -> bool:
        key = (symbol, timeframe)

        return self._is_new_bar[key]
    
    # TODO    
    @_synchronized_market_data
    def get_latest_quote(self, symbol: str) -> Quote | None:
        self._validate_symbol(symbol)
        normalized_symbol = str(symbol).strip().upper()
        subscription = self._symbol_subscriptions.get(normalized_symbol)
        if subscription is None or not subscription["quotes"]:
            raise LookupError(
                f"{normalized_symbol} quotes were not subscribed in on_init()"
            )

        quote = self._quotes.get(normalized_symbol)
        if quote is None:
            self._log_data_unavailable_once(
                data_type="quote",
                symbol=normalized_symbol,
            )
            return None

        self._mark_data_available(data_type="quote", symbol=normalized_symbol)
        return Quote(
            ts=quote.ts.astype("datetime64[ms]").tolist(),
            bid_price=float(quote.bid_price),
            bid_size=float(quote.bid_size),
            ask_price=float(quote.ask_price),
            ask_size=float(quote.ask_size),
        )

    @_synchronized_market_data
    def update_quote(self, symbol: str, quote: _QuoteRow) -> None:
        self._validate_symbol(symbol)
        self._quotes[symbol] = quote
    
    @_synchronized_market_data
    def get_best_bid(self, symbol: str) -> float | None:
        self._validate_symbol(symbol)
        quote = self._quotes.get(symbol)
        return None if quote is None else float(quote.bid_price)

    @_synchronized_market_data
    def get_best_ask(self, symbol) -> float | None:
        self._validate_symbol(symbol)
        quote = self._quotes.get(symbol)
        return None if quote is None else float(quote.ask_price)
    
    @_synchronized_market_data
    def get_spread(self, symbol) -> float | None:
        self._validate_symbol(symbol)
        quote = self._quotes.get(symbol)
        if quote is None:
            return None
        return float(quote.ask_price - quote.bid_price)
    
    def get_daily_summaries(
        self,
        symbols: list[str] | str = "ALL",
    ) -> Mapping[str, Bar] | None:
        """
        Return the previous day's stock summary by symbol.

        Parameters
        ----------
        symbols
            Symbols whose daily summaries are requested, or ``"ALL"`` to request
            every available symbol.

        Returns
        -------
        Mapping[str, Bar] | None
            Mapping from each symbol to its daily OHLCV bar, or ``None`` when no
            daily summary data is available.
        """
        self._validate_symbols(symbols)

        date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        df = self._storage_client.get_daily_stock_summary(date=date)

        if df is None:
            return None

        if symbols != "ALL":
            df = df[df["symbol"].isin(set(symbols))]

        bar_timestamp = datetime.strptime(
            date,
            "%Y-%m-%d",
        ).replace(tzinfo=timezone.utc)

        return {
            row.symbol: Bar(
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                ts=bar_timestamp,
            )
            for row in df.itertuples(index=False)
    }

    def reference(self, fields, symbols):
        ## TODO
        ...

    def get_fundamentals(
        self,
        fields: list[FinancialFactor] | str = "ALL",
        symbols: list[str] | str = "ALL",
    ) -> Mapping[FinancialFactor, Mapping[str, float]] | None:
        """
        Return fundamental values grouped by financial factor.

        Parameters
        ----------
        fields
            Financial factors to return, or ``"ALL"`` to return every available
            financial factor.
        symbols
            Symbols to return, or ``"ALL"`` to return every available symbol.

        Returns
        -------
        Mapping[FinancialFactor, Mapping[str, float]] | None
            Mapping from each financial factor to a symbol-value mapping, or
            ``None`` when fundamental data is unavailable.

        Examples
        --------
        ```python
        fundamentals = self.data.fundamentals(
            fields=[
                FinancialFactor.PE_RATIO,
                FinancialFactor.MARKET_CAP,
            ],
            symbols=["AAPL", "MSFT"],
        )

        if fundamentals is not None:
            apple_pe = fundamentals[FinancialFactor.PE_RATIO]["AAPL"]
        ```
        """
        self._validate_symbols(symbols)

        df = self._storage_client.get_fundamentals()

        if df is None:
            return None

        if symbols != "ALL":
            symbol_set = set(symbols)
            df = df[df["symbol"].isin(symbol_set)]

        if fields == "ALL":
            field_list = [
                FinancialFactor(column)
                for column in df.columns
                if column != "symbol"
            ]
        else:
            field_list = fields

        symbol_list = df["symbol"].astype(str).tolist()

        return {
            field: {
                symbol: float(value)
                for symbol, value in zip(
                    symbol_list,
                    df[field.value].tolist(),
                    strict=True,
                )
            }
            for field in field_list
        }

    def new_data_handler(
        self,
        event: dict
    ):
        if event["type"] == "tick":
            data = event["payload"]
            self.update_ticks(data.pop("symbol"), data)
        elif event["type"] == "quote":
            data = event["payload"]
            self._quotes[data.pop("symbol")] = data

    def _validate_symbol(
        self,
        symbol: str,
    ) -> None:
        check_result = self._symbol_reference_service.check(symbol)

        if not check_result.valid:
            self._logger.platform_error(
                message=f"{symbol} is not available",
                reason=str(check_result.reason)
            )
            self._logger.error(
                message=f"{symbol} is not available",
                reason=str(check_result.reason)
            )
            self._submit_coroutine(
                self._status_manager.transform(Status.FAILED)
            )
            

    def _validate_symbols(
        self,
        symbols: list[str] | str = "ALL",
    ) -> None:
        """
        Validate symbol selection input.

        This helper is not part of the public strategy API.
        """
        if symbols == "ALL":
            return

        if not isinstance(symbols, (list, tuple)):
            raise InvalidValueError(
                message="symbols must be a list, tuple, or 'ALL'",
                details={"symbols": symbols},
            )

        if len(symbols) == 0:
            raise InvalidValueError(
                message="symbols must not be empty",
                details={"symbols": symbols},
            )

        for symbol in symbols:
            self._validate_symbol(symbol)

    def _validate_fields(
        self,
        fields: list[FinancialFactor],
    ) -> None:
        """
        Validate requested fields.

        This helper is not part of the public strategy API.
        """
        if isinstance(fields, FinancialFactor):
            return

        if not isinstance(fields, (list, tuple)):
            raise InvalidValueError(
                message="fields must be a FinancialFactor, list, or tuple",
                details={"fields": fields},
            )

        if len(fields) == 0:
            raise InvalidValueError(
                message="fields must not be empty",
                details={"fields": fields},
            )

        for field in fields:
            if not isinstance(field, FinancialFactor):
                raise InvalidValueError(
                    message="field must be a FinancialFactor",
                    details={"field": field},
                )

    def _resolve_history_limit(
        self,
        limit: int | None,
    ) -> int:
        """
        Resolve and validate the history() limit.

        This helper is not part of the public strategy API.
        """
        if limit is None:
            return DEFAULT_BAR_LIMIT

        if limit <= 0:
            raise InvalidValueError(
                message="history limit must be greater than 0",
                details={"limit": limit},
            )

        if limit > MAX_BAR_LIMIT:
            raise InvalidValueError(
                message="history limit exceeds the maximum allowed value",
                details={
                    "limit": limit,
                    "maximum": MAX_BAR_LIMIT,
                },
            )

        return limit

    def _resolve_tick_limit(
        self,
        limit: int | None,
    ) -> int:
        """
        Resolve and validate the ticks() limit.

        This helper is not part of the public strategy API.
        """
        if limit is None:
            return DEFAULT_TICK_LIMIT

        if limit <= 0:
            raise InvalidValueError(
                message="tick limit must be greater than 0",
                details={"limit": limit},
            )

        if limit > MAX_TICK_LIMIT:
            raise InvalidValueError(
                message="tick limit exceeds the maximum allowed value",
                details={
                    "limit": limit,
                    "maximum": MAX_TICK_LIMIT,
                },
            )

        return limit
