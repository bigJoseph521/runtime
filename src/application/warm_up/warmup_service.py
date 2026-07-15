from __future__ import annotations

import time

from alphovex_sdk import Timeframe

from application.context.logging_context import RuntimeLoggingContext
from application.event_handling.external_event_bus import ExternalEventBus
from application.event_handling.events_model import ExternalEventType, InternalEventType
from application.event_handling.internal_event_bus import InternalEventBus
from infrastructure.http.hds_client import HistoricalDataServiceClient


class WarmUpService:
    def __init__(
        self,
        hds_client: HistoricalDataServiceClient,
        logger: RuntimeLoggingContext,
        external_event_bus: ExternalEventBus,
        internal_event_bus: InternalEventBus
    ):
        self._hds_client = hds_client
        self._logger = logger
        self._external_event_bus = external_event_bus
        self._internal_event_bus = internal_event_bus

    async def warm_up(
        self,
        symbol: str,
        timeframe: Timeframe,
        window: int,
    ) -> None:
        _BarRows = await self._hds_client.get_bar_history(
            symbol=symbol,
            timeframe=timeframe,
            window=window,
        )


        if _BarRows is None:
            self._logger.platform_error(
                message="Failed to fetch warm-up data",
                symbol=symbol,
                timeframe=timeframe,
                window=window,
            )

            return

        total = len(_BarRows)

        # The HDS response is expected to be ordered:
        # oldest bar -> newest bar.
        for index, bar in enumerate(_BarRows):
            self._logger.platform_info(
                message="warm up data is being replayed",
                remain_num=total - index - 1,
                symbol=symbol,
                timeframe=timeframe,
                window=window,
            )

            self._external_event_bus.publish(
                {
                    "type": ExternalEventType.WARMUP_BAR,
                    "payload": {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "bar": bar,
                    },
                }
            )

        # Publish exactly once after all historical bars have been
        # passed to DataContext and IndicatorContext.
        await self._internal_event_bus.publish(
            {
                "type": InternalEventType.WARMUP_FINISHED,
                "payload": {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "window": window,
                },
            }
        )

