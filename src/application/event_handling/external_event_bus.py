from __future__ import annotations

from collections import defaultdict

from typing import Callable, TYPE_CHECKING

from application.event_handling.events_model import ExternalEventType

if TYPE_CHECKING:
    from application.context.data_context import RuntimeDataContext
    from application.context.order_context import RuntimeOrderContext
    from application.context.time_context import RuntimeTimeContext

class ExternalEventBus:
    def __init__(self):
        self._consumers : defaultdict[ExternalEventType, list[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: ExternalEventType, handler):
        self._consumers[event_type].append(handler)
    
    def publish(self, event):
        event_type = event["type"]

        if event_type in (
            ExternalEventType.TICK,
            ExternalEventType.QUOTE
        ):
            for handler in self._consumers[event_type]:
                handler(event["symbol"], event["payload"])        
        elif event_type == ExternalEventType.CURRENT_BAR:
            for handler in self._consumers[event_type]:
                handler(
                    event["symbol"],
                    event["timeframe"],
                    event["payload"],
                    event.get("completed", False),
                )
        elif event_type == ExternalEventType.WARMUP_BAR:
            for handler in self._consumers[event_type]:
                handler(
                    event["payload"]["symbol"],
                    event["payload"]["timeframe"],
                    event["payload"]["bar"],
                    True
                )        
        elif event_type == ExternalEventType.ORDER_UPDATE:
            for handler in self._consumers[event_type]:
                handler()

def create_external_bus(
    data_context: RuntimeDataContext,
    order_context: RuntimeOrderContext,
    time_context: RuntimeTimeContext
) -> ExternalEventBus:
    event_bus = ExternalEventBus()

    event_bus.subscribe(
        event_type=ExternalEventType.TICK,
        handler=data_context.update_ticks
    )
    event_bus.subscribe(
        event_type=ExternalEventType.TICK,
        handler=time_context.update_time_from_market_data
    )

    event_bus.subscribe(
        event_type=ExternalEventType.QUOTE,
        handler=data_context.update_quote
    )
    event_bus.subscribe(
        event_type=ExternalEventType.QUOTE,
        handler=time_context.update_time_from_market_data
    )

    event_bus.subscribe(
        event_type=ExternalEventType.CURRENT_BAR,
        handler=data_context.update_bars
    )

    event_bus.subscribe(
        event_type=ExternalEventType.ORDER_UPDATE,
        handler=order_context.update_order_status
    )

    return event_bus

    # event_bus.subscribe(
    #     event_type=ExternalEventType.PORTFOLIO_UPDATE
    # )
