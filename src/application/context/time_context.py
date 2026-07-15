from __future__ import annotations

from typing import Any

from datetime import datetime, timedelta, timezone, time

from alphovex_sdk.context.time_context import TimeContext
from alphovex_sdk.typedefs.aliases import Symbol
from alphovex_sdk.models.session import MarketSession

from alphovex_sdk import (
    TimeContext,
    Symbol,
    MarketStatus
)

from application.event_handling.internal_event_bus import InternalEventBus
from application.context.logging_context import RuntimeLoggingContext

class RuntimeTimeContext(TimeContext):
    def __init__(
        self, 
        event_bus: InternalEventBus,
        logger: RuntimeLoggingContext
    ):
        self._event_bus = event_bus
        self._timer_interval: int = 0
        self._timer_healthy: bool = False
        self._now = datetime.now()
        self._market_status: MarketStatus | None = None
        self._next_timer_at: datetime | None = None
        self._logger = logger
    
    def now(self):
        return self._now
    
    def today(self):
        return self._now.date()
    
    def update(self, new_time: datetime):
        self._now = new_time
        if self._timer_healthy:
            self._check_timer()
    
    def is_market_open(self, symbol: Symbol | None = None) -> bool:
        return self._market_status == MarketStatus.OPEN
    
    def current_session(self, symbol: Symbol | None = None) -> MarketStatus:
        if self._market_status is None:
            return time(9, 30) <= self._now.time() <= time(16, 0) 
        return self._market_status
        
    def set_timer(self, interval: int):
        self._timer_interval = interval
        self._timer_healthy = True
        self._next_timer_at = self._now
        
    def kill_timer(self):
        self._timer_interval = 0
        self._timer_healthy = True
    
    def _check_timer(self):
        if self._now > self._next_timer_at:
            self._event_bus.publish({
                "type": "timer",
                "payload": {}
            })
            self._logger.platform_info(
                message="Timer event emiited",
                now = str(self._now),
                expected = str(self._next_timer_at),
                diff = str((self._now - self._next_timer_at).total_seconds())
            )
            self._next_timer_at += timedelta(seconds=self._timer_interval)
    
    def update_time_from_market_data(self, _: Any, data: Any):
        new_time = data.ts.item()
        new_time_utc = new_time.replace(tzinfo=timezone.utc)
        pc_time_utc = datetime.now().astimezone(tz = timezone.utc)
        self._logger.platform_info(
            message="Time updated",
            local_time = str(pc_time_utc),
            data_time = str(new_time_utc),
            diff = f"{str((pc_time_utc - new_time_utc).total_seconds())}s"
        )
        self.update(new_time)
    
    def update_session(self, new_status: MarketStatus)-> None:
        self._market_status = new_status

    

