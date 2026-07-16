from __future__ import annotations

from typing import Any
from collections import deque
from dataclasses import dataclass
import uuid
import asyncio
import time
from datetime import datetime

from alphovex_sdk import (
    Bar,
    Timeframe,
    Indicator,
    MAX_INDICATOR_HISTORY_SIZE,
    MIN_INDICATOR_HISTORY_SIZE,
    DEFAULT_INDICATOR_HISTORY_SIZE,
    IndicatorUpdateMode,
    IndicatorContext
)
from application.status_managing.manager import StatusManager
from application.status_managing.status_model import Status
from application.context.logging_context import RuntimeLoggingContext
from application.event_handling.internal_event_bus import InternalEventBus, InternalEventType
from application.symbol_reference.symbol_reference import SymbolReferenceService
from contracts.rows import _BarRow

@dataclass(frozen=True)
class IndicatorHandle:
    key: str

@dataclass(frozen=False)
class _RegisteredIndicator:

    handle: IndicatorHandle
    indicator: Indicator
    symbol: str
    timeframe: Timeframe
    update_mode: IndicatorUpdateMode
    value_history: deque[Any]
    warmup_finished: bool
    warmup_replayed: bool
    recently_updated: bool
    bars: deque[Bar]


class RuntimeIndicatorContext(IndicatorContext):

    def __init__(
            self, 
            internal_event_bus: InternalEventBus,
            status_manager: StatusManager,
            logger: RuntimeLoggingContext,
            symbol_reference_service: SymbolReferenceService
        ) -> None:
        """
        Initialize an empty IndicatorContext.
        """

        self._indicators: dict[IndicatorHandle, _RegisteredIndicator] = {}
        self._internal_event_bus = internal_event_bus
        self._status_manager = status_manager
        self._logger = logger
        self._symbol_reference_service = symbol_reference_service
        self._pending_warmup_windows: dict[
            tuple[str, Timeframe], int
        ] = {}

        self._warmup_request_tasks: dict[
            tuple[str, Timeframe], asyncio.Task[None]
        ] = {}
        
    def register(
        self,
        indicator: Indicator, 
        symbol: str, 
        timeframe: Timeframe,
        *,
        update_mode: IndicatorUpdateMode = IndicatorUpdateMode.BAR,
        history_size: int | None = None
    ) -> IndicatorHandle:
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

            raise ValueError(
                f"{symbol} is not available for {str(check_result.reason)}"
            )
        
        handle = IndicatorHandle(str(uuid.uuid4()))
        record = _RegisteredIndicator(
            handle, 
            indicator, 
            symbol, 
            timeframe, 
            update_mode,
            deque(maxlen=history_size), 
            False,
            False,
            False,
            deque(maxlen=indicator.required_history)
        )
        self._indicators[handle] = record
        target = (symbol, timeframe)

        self._pending_warmup_windows[target] = max(
            indicator.required_history,
            self._pending_warmup_windows.get(target, 0),
        )

        existing_task = self._warmup_request_tasks.get(target)

        if existing_task is None or existing_task.done():
            self._start_warmup_task(target)

        return handle

    def _start_warmup_task(
        self,
        target: tuple[str, Timeframe],
    ) -> None:
        task = asyncio.create_task(
            self._publish_coalesced_warmup_request(target),
            name=f"indicator-warmup:{target[0]}:{target[1]}",
        )
        task.add_done_callback(self._observe_warmup_task)
        self._warmup_request_tasks[target] = task

    def _observe_warmup_task(
        self,
        task: asyncio.Task[None],
    ) -> None:
        """Retrieve background failures so asyncio never reports orphan tasks."""
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            self._logger.platform_error(
                message="Indicator warm-up task failed",
                error=str(error),
                task_name=task.get_name(),
            )
            asyncio.create_task(
                self._status_manager.transform(Status.FAILED)
            )

    @property
    def all_ready(self) -> bool:
        """Return whether every active indicator has completed warm-up.

        An empty registration set is ready. This lets strategies that do not
        use indicators receive ticks normally while creating a strategy-wide
        readiness barrier as soon as any indicator is registered.
        """
        return all(
            registered.warmup_finished
            for registered in self._indicators.values()
        )

    @property
    def registered_targets(self) -> list[tuple[str, Timeframe]]:
        """Return the unique symbol/timeframe targets currently in use."""
        return list({
            (registered.symbol, registered.timeframe)
            for registered in self._indicators.values()
        })

    async def wait_for_pending_warmups(self) -> None:
        """Wait for registrations already issued by strategy initialization.

        Registrations created later remain asynchronous. The market-data
        pipeline continues running, but strategy tick callbacks pause until
        every active registration is ready.
        """
        initial_handles = tuple(self._indicators)
        await asyncio.sleep(0)

        while self._warmup_request_tasks:
            tasks = tuple(self._warmup_request_tasks.values())
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, BaseException):
                    raise RuntimeError(
                        "Indicator warm-up failed during strategy startup"
                    ) from result
            await asyncio.sleep(0)

        not_ready = [
            self._indicators[handle]
            for handle in initial_handles
            if handle in self._indicators
            and not self._indicators[handle].warmup_finished
        ]
        if not_ready:
            targets = sorted({
                f"{item.symbol}:{item.timeframe}"
                for item in not_ready
            })
            raise RuntimeError(
                "Indicator warm-up produced no value for: "
                + ", ".join(targets)
            )
    
    async def _publish_coalesced_warmup_request(
        self,
        target: tuple[str, Timeframe],
    ) -> None:
        # Allow all indicators registered during on_init() to be collected.
        await asyncio.sleep(0)

        symbol, timeframe = target
        window = self._pending_warmup_windows.pop(target, 0)

        try:
            await self._internal_event_bus.publish(
                event={
                    "type": InternalEventType.INDICATOR_REGISTERED,
                    "payload": {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "window": window,
                    },
                }
            )
        finally:
            self._warmup_request_tasks.pop(target, None)

            if target in self._pending_warmup_windows:
                self._start_warmup_task(target)
    def get_value(
        self,
        handle
    ) -> tuple[Any, bool]:
        registered = self._indicators.get(handle)
        
        if not registered:
            self._logger.error(
                message="Indicator not registered"       
            )
            self._logger.platform_error(
                message="Indicator not registered",
                source="user"
            )
            asyncio.create_task(
                self._status_manager.transform(new_status=Status.FAILED)
            )

            time.sleep(1.0)

            raise ValueError(
                "Indicator not registered"
            )

        if not registered.value_history:
            return None, False

        return registered.value_history[0], registered.recently_updated
        
    def get_values(
        self,
        handle: IndicatorHandle,
        *,
        start: int = 0,
        count: int = 1,
    ) -> tuple[Any, ...]:
        """
        Return calculated indicator values from newest to oldest.

        Parameters
        ----------
        handle
            Handle returned by ``IndicatorContext.register()``.
        start
            Zero-based offset from the newest calculated value.
        count
            Maximum number of values to return.

        Returns
        -------
        tuple[Any, ...]
            Indicator values ordered from newest to oldest.

            An empty tuple is returned when ``start`` is beyond the available
            history.

        Raises
        ------
        ValueError
            If ``start`` is negative, ``count`` is less than one, or the
            indicator handle is not registered.
        """
        if start < 0:
            message = "'start' must be a non-negative integer"

            self._logger.error(
                message=message,
                start=start,
            )
            self._logger.platform_error(
                message=message,
                source="user",
                start=start,
            )

            raise ValueError(message)

        if count < 1:
            message = "'count' must be a positive integer"

            self._logger.error(
                message=message,
                count=count,
            )
            self._logger.platform_error(
                message=message,
                source="user",
                count=count,
            )

            raise ValueError(message)

        registered = self._indicators.get(handle)

        if registered is None:
            message = "Indicator handle is not registered"

            self._logger.error(
                message=message,
                handle=handle,
            )
            self._logger.platform_error(
                message=message,
                source="user",
                handle=handle,
            )

            raise ValueError(message)

        values = tuple(registered.value_history)

        return values[start : start + count]

    def unregister(self, handle: IndicatorHandle) -> bool:
        if not handle in self._indicators:
            self._logger.warning(
                message="Indicator not registered"       
            )
            self._logger.platform_warning(
                message="Indicator not registered",
                source="user"
            )

            return True

        registered = self._indicators.pop(handle)

        symbol = registered.symbol
        timeframe = registered.timeframe

        target_is_still_used = any(
            item.symbol == symbol and item.timeframe == timeframe
            for item in self._indicators.values()
        )

        if not target_is_still_used:
            self._symbol_reference_service.unregister(symbol)
            self._cancel_pending_warmup((symbol, timeframe))

            asyncio.create_task(
                self._internal_event_bus.publish(
                    event={
                        "type": InternalEventType.INDICATOR_UNREGISTERED,
                        "payload": {
                            "symbol": symbol,
                            "timeframe": timeframe,
                        },
                    }
                )
            )

    def unregister_all(self) -> None:
        """
        Unregister all indicators matching optional filter.
        Returns the number of indicators removed.
        """
        # Decide whethere remove symbol ref in registry service
        symbols = set()
        for handle in self._indicators:
            symbols.add(self._indicators[handle].symbol)
        
        for symbol in symbols:
            self._symbol_reference_service.unregister(symbol)

        self._indicators = {}

        for target in list(self._warmup_request_tasks):
            self._cancel_pending_warmup(target)

        self._pending_warmup_windows.clear()

        asyncio.create_task(
            self._internal_event_bus.publish(
                event={
                    "type": InternalEventType.INDICATOR_ALL_UNREGISTERED,
                    "payload": {},
                }
            )
        )

    def update_indicator(
        self,
        symbol: str,
        timeframe: str,
        bar: _BarRow,
        completed: bool,
    ) -> None:

        matching_indicators = []
        for registered in self._indicators.values():
            registered.recently_updated = False
            if (
                (registered.symbol, registered.timeframe) == (symbol, timeframe)
                and (
                    registered.warmup_finished
                    or registered.warmup_replayed
                )
            ):
                matching_indicators.append(registered)

        if not matching_indicators:
            return

        if bar is None:
            self._logger.platform_error(
                message="Received None bar in update_indicator",
                symbol=symbol,
                timeframe=timeframe,
            )
            return
        
        runtime_bar = Bar(
            ts=bar.ts.astype(datetime),
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume),
        )

        updated_count = 0

        for registered in matching_indicators:
            value: Any | None = None
            
            registered.bars.appendleft(runtime_bar)
            if completed:
                value = registered.indicator.calculate(
                    list(registered.bars),
                    is_new_bar = True,
                )

                updated_count += 1

            elif (
                registered.update_mode
                == IndicatorUpdateMode.TICK
            ):
                value = registered.indicator.calculate(
                    list(registered.bars),
                    is_new_bar = False,
                )

                updated_count += 1

            if value is not None:
                registered.warmup_finished = True
                registered.recently_updated = True
                registered.value_history.appendleft(
                    value,
                )
            
            self._logger.platform_info(
                message="Indicator calculations finished",
                symbol=symbol,
                timeframe=timeframe,
                window= registered.indicator.required_history,
                value=value,
                indicator_count=updated_count,
            )

    def update_warmup_indicator(
        self,
        symbol: str,
        timeframe: str,
        bar: _BarRow,
        completed: bool,
    ) -> None:
        """Replay history only into indicators that are still warming."""
        if bar is None:
            return

        runtime_bar = Bar(
            ts=bar.ts.astype(datetime),
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=float(bar.volume),
        )

        for registered in self._indicators.values():
            if (
                (registered.symbol, registered.timeframe)
                != (symbol, timeframe)
                or registered.warmup_finished
            ):
                continue

            registered.bars.appendleft(runtime_bar)
            value = registered.indicator.calculate(
                list(registered.bars),
                is_new_bar=completed,
            )
            if value is not None:
                registered.value_history.appendleft(value)

    async def complete_warmup(
        self,
        symbol: str,
        timeframe: Timeframe,
        _: int,
    ) -> None:
        """Commit warm-up readiness for the requested target."""
        matching = [
            registered
            for registered in self._indicators.values()
            if (
                (registered.symbol, registered.timeframe)
                == (symbol, timeframe)
                and not registered.warmup_finished
            )
        ]

        for registered in matching:
            registered.warmup_replayed = True
            registered.warmup_finished = bool(
                registered.value_history
            )
            registered.recently_updated = False

        not_ready = [
            registered for registered in matching
            if not registered.warmup_finished
        ]
        if not_ready:
            raise RuntimeError(
                "Insufficient historical bars to warm indicators for "
                f"{symbol}:{timeframe}"
            )
