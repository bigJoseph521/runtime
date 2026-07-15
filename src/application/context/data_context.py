from __future__ import annotations

from typing import Any
from collections.abc import Mapping
import asyncio
from datetime import datetime, timedelta, timezone
import numpy as np
import math

from alphovex_sdk import(
    DataContext,
    MAX_BAR_LIMIT,
    MAX_TRADE_LIMIT,
    DEFAULT_BAR_LIMIT,
    DEFAULT_TRADE_LIMIT,
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
        self._tick_buffer_size = MAX_TRADE_LIMIT

        self._bars : dict[tuple[str, str], BarRingBuffer] = {}
        self._ticks : dict[str, TickRingBuffer] = {}
        self._quotes: dict[str, _QuoteRow] = {}
        self._bar_completed: dict[tuple[str, Timeframe], bool] = {}

        self._storage_client = storage_client
        self._logger = logger
        self._event_bus = event_bus
        self._symbol_reference_service = symbol_reference_service
        self._status_manager = status_manager
        self._hds_client = hds_client

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

    #--------------------
    # Runtime Functions
    #--------------------

    def update_bars(self, symbol:str, tf: str, bar:_BarRow, completed: bool):
        buf = self._get_bar_buffer(symbol, tf)

        key = (symbol, tf)

        self._bar_completed[key] = completed

        if completed:
            buf.append(bar=bar)
        else:
            buf.update_current_bar(bar=bar)        

    def update_ticks(self, symbol: str, tick:_TickRow):
        buf = self._get_tick_buffer(symbol)

        buf.append(tick=tick)


    #--------------------------
    # SDK Functions
    #--------------------------
    
    def get_latest_bars(self, symbol, timeframe, *, start, count, limit = None):
        self._validate_symbol(symbol)
        buf = self._get_bar_buffer(symbol=symbol, tf=timeframe)
        # TODO
        if buf.size == 0:    
            _BarRows = self._hds_client.get_bar_history(
                symbol=symbol,
                timeframe=timeframe,
                window= start + count
            )
            if _BarRows is not None:
                for i in len(_BarRows):
                    buf.append(_BarRows[i+start])
        

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
        
        return tuple(
            Bar(
                open = float(open_[i]),
                high = float(high[i]),
                low = float(low[i]),
                close = float(close[i]),
                volume = float(volume[i]),
                ts= ts[i].astype("datetime64[ms]").to_list()
            )
            for i in range(ts.shape[0])
        )

    def get_latest_trades(self, symbol, *, start, count, limit = None):
        self._validate_symbol(symbol)
        buf = self._get_tick_buffer(symbol)

        #TODO
        # if buf.size == 0
        #   update buf

        ts = buf.view("ts")
        price = buf.view("price")
        volume = buf.view("volume")

        end = min(start + count, buf.size)

        ts = ts[start:end]
        price = price[start:end]
        volume = volume[start:end]

        return tuple(
            Tick(
                ts= ts[i].astype("datetime64[ms]").to_list(),
                price= float(price[i]),
                volume= float(volume[i]) 
            )
            for i in range(count)
        )

    def get_current_bar(self, symbol:str, tf:str) -> Bar:
        self._validate_symbol(symbol)
        buf = self._get_bar_buffer(symbol,tf)

        if buf.size == 0:
            return None
        
        i = (buf.head - 1) % buf.capacity

        return Bar({
            "ts": int(buf.ts[i]),
            "open": float(buf.open[i]),
            "high":float(buf.high[i]),
            "low": float(buf.low[i]),
            "close": float(buf.close[i]),
            "volume": float(buf.volume[i])
        })

    def get_latest_trade(self, symbol: str) -> Tick:
        self._validate_symbol(symbol)
        buf = self._get_tick_buffer(symbol=symbol)
        
        if buf.size == 0:
            return None
        
        i = (buf.head - 1) % buf.capacity

        return Tick({
            "ts": buf.ts[i],
            "price": buf.price[i],
            "volume": buf.volume[i]
        })       

    def is_new_bar(self, symbol, timeframe) -> bool:
        ...
    
    # TODO    
    def get_latest_quote(self, symbol: str):
        self._validate_symbol(symbol)
        return self._quotes[symbol]

    def update_quote(self, symbol:str, quote: Quote):
        self._validate_symbol(symbol)
        self._quotes[symbol]=self.quote
    
    def get_best_bid(self, symbol: str) -> float:
        self._validate_symbol(symbol)
        return self._quotes[symbol].bid

    def get_best_ask(self, symbol) -> float:
        self._validate_symbol(symbol)
        return self._quotes[symbol].ask
    
    def get_spread(self, symbol) -> float:
        self._validate_symbol(symbol)
        temp_quote = self._quotes[symbol]
        return temp_quote.bid - temp_quote.ask
    
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
            asyncio.create_task(
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

    def _resolve_trade_limit(
        self,
        limit: int | None,
    ) -> int:
        """
        Resolve and validate the trades() limit.

        This helper is not part of the public strategy API.
        """
        if limit is None:
            return DEFAULT_TRADE_LIMIT

        if limit <= 0:
            raise InvalidValueError(
                message="trade limit must be greater than 0",
                details={"limit": limit},
            )

        if limit > MAX_TRADE_LIMIT:
            raise InvalidValueError(
                message="trade limit exceeds the maximum allowed value",
                details={
                    "limit": limit,
                    "maximum": MAX_TRADE_LIMIT,
                },
            )

        return limit