from __future__ import annotations

from typing import Final

from .account_context import AccountContext
from .data_context import DataContext
from .logging_context import LoggingContext
from .order_context import OrderContext
from .params_context import ParamsContext
from .time_context import TimeContext
from .indicator_context import IndicatorContext
from .position_context import PositionContext
from .storage_context import StorageContext

class StrategyContext:
    def __init__(
        self,
        account_context: AccountContext,
        data_context: DataContext,
        indicator_context: IndicatorContext,
        logging_context: LoggingContext,
        order_context: OrderContext,
        params_context: ParamsContext,
        position_context: PositionContext,
        time_context: TimeContext,
        storage_context: StorageContext
    ):
        self._account_context = account_context
        self._data_context = data_context
        self._indicator_context = indicator_context
        self._logging_context = logging_context
        self._order_context = order_context
        self._params_context = params_context
        self._position_context = position_context
        self._time_context = time_context
        self._storage_context = storage_context

    @property
    def account(self) -> AccountContext:
        return self._account_context
    
    @property
    def data(self) -> DataContext:
        return self._data_context

    @property
    def indicator(self) -> IndicatorContext:
        return self._indicator_context

    @property
    def logging(self) -> LoggingContext:
        return self._logging_context
    
    @property
    def order(self) -> OrderContext:
        return self._order_context
    
    @property
    def params(self) -> ParamsContext:
        return self._params_context
    
    @property
    def position(self) -> PositionContext:
        return self._position_context
    
    @property
    def time(self) -> TimeContext:
        return self._time_context
    
    @property
    def storage(self) -> StorageContext:
        return self._storage_context


    