from __future__ import annotations

from enum import StrEnum

class InternalEventType(StrEnum):
    STATUS_CHANGED = "status_changed"
    WARMUP_FINISHED = "warmup_finished"
    STRATEGY_CALCULATION_FINISHED = "strategy_calculation_finished"
    INDICATOR_REGISTERED = "indicator_registered"
    INDICATOR_UNREGISTERED = "indicator_unregistered"
    INDICATOR_ALL_UNREGISTERED = "indicator_all_unregistered"

class ExternalEventType(StrEnum):
    TICK = "tick"
    QUOTE = "quote"
    CURRENT_BAR = "current_bar"
    ORDER_UPDATE = "order_update"
    SIGTERM = "sigterm"
    WARMUP_BAR = "warmup_bar"
    INDEX_BAR = "index_bar"
    INDEX_VALUE = "index_value"
    TIMEFRAME_APPLIED = "timeframe_applied"
