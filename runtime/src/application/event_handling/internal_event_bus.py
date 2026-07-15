from __future__ import annotations

from datetime import datetime

from collections import defaultdict

from typing import Callable

from application.event_handling.events_model import InternalEventType

class InternalEventBus:
    def __init__(self):
        self._consumers : defaultdict[InternalEventType, list[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: InternalEventType, handler):
        self._consumers[event_type].append(handler)
    
    async def publish(self, event):
        event_type = event["type"]

        if event_type == InternalEventType.STATUS_CHANGED:
            for handler in self._consumers[event_type]:
                await handler(event["new_status"])

        elif event_type == InternalEventType.INDICATOR_REGISTERED:
            for handler in self._consumers[event_type]:
                await handler(
                    event["payload"]["symbol"],
                    event["payload"]["timeframe"],
                    event["payload"]["window"],
                )

        elif event_type == InternalEventType.INDICATOR_UNREGISTERED:
            for handler in self._consumers[event_type]:
                await handler(
                    event["payload"]["symbol"],
                    event["payload"]["timeframe"],
                    None,
                )

        elif event_type == InternalEventType.INDICATOR_ALL_UNREGISTERED:
            for handler in self._consumers[event_type]:
                await handler()
        
        elif event_type == InternalEventType.WARMUP_FINISHED:
            for handler in self._consumers[event_type]:
                await handler(event["payload"]["symbol"], event["payload"]["timeframe"], event["payload"]["window"])
        


        
        