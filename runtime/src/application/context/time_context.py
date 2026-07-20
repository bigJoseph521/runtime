from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import Any

from alphovex_sdk import MarketStatus, Symbol, TimeContext

from application.context.logging_context import RuntimeLoggingContext
from application.event_handling.internal_event_bus import InternalEventBus


class RuntimeTimeContext(TimeContext):
    """
    Provides strategy time, market-event time, session status, and periodic
    strategy timer events.

    Runtime time follows the system's UTC clock. Market-event time contains
    the timestamp of the latest accepted tick, quote, or bar.

    Timers run independently from market-data arrival, so they continue
    during quiet periods and outside market sessions.
    """

    def __init__(
        self,
        event_bus: InternalEventBus,
        logger: RuntimeLoggingContext,
    ) -> None:
        self._event_bus = event_bus
        self._logger = logger

        self._market_status: MarketStatus | None = None
        self._last_market_event_time: datetime | None = None

        self._timer_interval: float | None = None
        self._next_timer_at: datetime | None = None
        self._timer_task: asyncio.Task[None] | None = None
        self._timer_changed = asyncio.Event()

        self._running = False

    # ------------------------------------------------------------------
    # Runtime lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """
        Start the runtime clock and timer dispatcher.

        The runtime must call this once during startup. Strategy code should
        use set_timer() and kill_timer() instead of calling start() directly.
        """
        if self._running:
            return

        self._running = True
        self._timer_task = asyncio.create_task(
            self._timer_loop(),
            name="runtime-time-context-timer",
        )

        self._logger.platform_info(
            message="Runtime time context started",
            now=str(self.now()),
        )

    async def stop(self) -> None:
        """
        Stop the timer dispatcher during runtime shutdown.
        """
        if not self._running:
            return

        self._running = False
        self._timer_changed.set()

        task = self._timer_task
        self._timer_task = None

        if task is not None:
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

        self._logger.platform_info(
            message="Runtime time context stopped",
            now=str(self.now()),
        )

    # ------------------------------------------------------------------
    # User-facing time API
    # ------------------------------------------------------------------

    def now(self) -> datetime:
        """
        Return the current timezone-aware UTC runtime time.

        This value continues advancing when the market is closed or no
        market-data messages are arriving.
        """
        return datetime.now(timezone.utc)

    def today(self):
        """
        Return the current UTC runtime date.
        """
        return self.now().date()

    @property
    def last_market_event_time(self) -> datetime | None:
        """
        Return the timestamp of the newest accepted market-data event.

        None is returned until the runtime receives its first market event.
        """
        return self._last_market_event_time

    def is_market_open(self, symbol: Symbol | None = None) -> bool:
        """
        Return whether the configured market session is currently open.

        The symbol argument is reserved for future symbol-specific exchange
        calendars.
        """
        del symbol

        if self._market_status is not None:
            return self._market_status == MarketStatus.OPEN

        # Temporary fallback when session status has not been supplied.
        # This uses UTC and therefore must not be treated as an ET calendar.
        return False

    def current_session(
        self,
        symbol: Symbol | None = None,
    ) -> MarketStatus:
        """
        Return the latest market status supplied to the runtime.

        Until session status is initialized, the market is considered closed.
        """
        del symbol

        if self._market_status is not None:
            return self._market_status

        return MarketStatus.CLOSED

    # ------------------------------------------------------------------
    # User-facing timer API
    # ------------------------------------------------------------------

    def set_timer(self, interval: int) -> None:
        """
        Request a repeating strategy timer.

        Parameters
        ----------
        interval:
            Number of seconds between timer events. It must be greater than
            zero.

        Runtime behavior
        ----------------
        The first timer event is emitted after one complete interval. Timer
        events continue while the market is quiet or closed. Calling this
        method again replaces the existing interval and restarts the timer.
        """
        if isinstance(interval, bool) or not isinstance(interval, int):
            raise TypeError("timer interval must be an integer number of seconds")

        if interval <= 0:
            raise ValueError("timer interval must be greater than zero")

        self._timer_interval = float(interval)
        self._next_timer_at = self.now() + timedelta(seconds=interval)
        self._timer_changed.set()

        self._logger.platform_info(
            message="Strategy timer configured",
            interval_seconds=interval,
            next_timer_at=str(self._next_timer_at),
        )

        self._logger.info(
            message="Strategy timer configured",
            interval_seconds=interval,
        )

    def kill_timer(self) -> None:
        """
        Stop the currently configured strategy timer.

        Calling this method when no timer is active has no effect.
        """
        was_active = self._timer_interval is not None

        self._timer_interval = None
        self._next_timer_at = None
        self._timer_changed.set()

        if was_active:
            self._logger.platform_info(
                message="Strategy timer stopped",
                now=str(self.now()),
            )

            self._logger.info(
                message="Strategy timer stopped",
            )

    # ------------------------------------------------------------------
    # Market-data time
    # ------------------------------------------------------------------

    def update_time_from_market_data(
        self,
        _: Any,
        data: Any,
    ) -> None:
        """
        Record the timestamp of the newest accepted market-data event.

        Delayed or out-of-order messages do not move the stored market-event
        time backward. Runtime wall-clock time is not changed.
        """
        try:
            market_time = self._extract_timestamp(data)
        except (AttributeError, TypeError, ValueError, OverflowError) as error:
            self._logger.platform_error(
                message="Invalid market-data timestamp",
                error_message=str(error),
                data_type=type(data).__name__,
            )
            return

        previous_time = self._last_market_event_time

        if previous_time is not None and market_time < previous_time:
            self._logger.platform_info(
                message="Out-of-order market-data timestamp ignored",
                market_time=str(market_time),
                last_market_event_time=str(previous_time),
                delay_seconds=(
                    previous_time - market_time
                ).total_seconds(),
            )
            return

        self._last_market_event_time = market_time

        runtime_time = self.now()

        self._logger.platform_info(
            message="Market-event time updated",
            runtime_time=str(runtime_time),
            market_event_time=str(market_time),
            transport_delay_seconds=max(
                0.0,
                (runtime_time - market_time).total_seconds(),
            ),
        )

    def update_session(
        self,
        new_status: MarketStatus,
    ) -> None:
        """
        Update the market-session status supplied by the runtime's session
        calendar or session-status service.
        """
        old_status = self._market_status
        self._market_status = new_status

        if old_status != new_status:
            self._logger.platform_info(
                message="Market session updated",
                old_status=(
                    old_status.value
                    if old_status is not None
                    else None
                ),
                new_status=new_status.value,
                now=str(self.now()),
            )

    # ------------------------------------------------------------------
    # Internal timer dispatcher
    # ------------------------------------------------------------------

    async def _timer_loop(self) -> None:
        while self._running:
            interval = self._timer_interval
            next_timer_at = self._next_timer_at

            if interval is None or next_timer_at is None:
                await self._wait_for_timer_change()
                continue

            delay = max(
                0.0,
                (next_timer_at - self.now()).total_seconds(),
            )

            changed = await self._wait_or_timer_change(delay)

            if changed or not self._running:
                continue

            # Re-read the configuration because set_timer() or kill_timer()
            # may have changed it while the task was sleeping.
            interval = self._timer_interval
            expected_at = self._next_timer_at

            if interval is None or expected_at is None:
                continue

            emitted_at = self.now()

            try:
                await self._event_bus.publish(
                    {
                        "type": "timer",
                        "payload": {
                            "expected_at": expected_at,
                            "emitted_at": emitted_at,
                            "delay_seconds": max(
                                0.0,
                                (emitted_at - expected_at).total_seconds(),
                            ),
                        },
                    }
                )
            except Exception as error:
                self._logger.platform_error(
                    message="Strategy timer handler failed",
                    error_message=str(error),
                    error_type=type(error).__name__,
                )

            self._logger.platform_info(
                message="Timer event emitted",
                emitted_at=str(emitted_at),
                expected_at=str(expected_at),
                delay_seconds=max(
                    0.0,
                    (emitted_at - expected_at).total_seconds(),
                ),
            )

            # Do not emit a burst of missed timer events. Move directly to the
            # next future deadline.
            next_at = expected_at

            while next_at <= emitted_at:
                next_at += timedelta(seconds=interval)

            self._next_timer_at = next_at

    async def _wait_for_timer_change(self) -> None:
        self._timer_changed.clear()
        await self._timer_changed.wait()

    async def _wait_or_timer_change(
        self,
        delay: float,
    ) -> bool:
        """
        Return True when timer configuration changed, or False when the
        deadline expired.
        """
        self._timer_changed.clear()

        try:
            await asyncio.wait_for(
                self._timer_changed.wait(),
                timeout=delay,
            )
            return True
        except asyncio.TimeoutError:
            return False

    @staticmethod
    def _extract_timestamp(data: Any) -> datetime:
        if not hasattr(data, "ts"):
            raise AttributeError("market-data object has no `ts` attribute")

        raw_timestamp = data.ts

        if isinstance(raw_timestamp, datetime):
            timestamp = raw_timestamp
        elif hasattr(raw_timestamp, "astype"):
            # Handles numpy.datetime64 without requiring pandas.
            timestamp = raw_timestamp.astype("datetime64[us]").item()
        elif hasattr(raw_timestamp, "item"):
            timestamp = raw_timestamp.item()
        else:
            timestamp = raw_timestamp

        if not isinstance(timestamp, datetime):
            raise TypeError(
                "market-data timestamp must resolve to datetime, "
                f"got {type(timestamp).__name__}"
            )

        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp.astimezone(timezone.utc)