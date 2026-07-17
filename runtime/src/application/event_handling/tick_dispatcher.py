from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from application.context.indicator_context import RuntimeIndicatorContext
    from application.strategy_execution.callback_executor import StrategyCallbackExecutor


class TickDispatcher:
    """Coalesce tick-triggered strategy calculations without queueing them."""

    def __init__(
        self,
        strategy: Any,
        indicator_context: RuntimeIndicatorContext,
        callback_executor: StrategyCallbackExecutor,
    ) -> None:
        self._strategy = strategy
        self._indicator_context = indicator_context
        self._callback_executor = callback_executor
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="strategy-calculation",
        )
        self._calculation_task: asyncio.Task[None] | None = None
        self._closed = False

    @property
    def calculation_running(self) -> bool:
        task = self._calculation_task
        return task is not None and not task.done()

    def dispatch(self, _symbol: str, _tick: Any) -> None:
        """Start on_tick only when no previous calculation is running."""
        if self._closed or self.calculation_running:
            return
        if not self._indicator_context.all_ready:
            return

        self._calculation_task = asyncio.create_task(
            self._run_calculation(),
            name="strategy-on-tick",
        )

    async def _run_calculation(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            self._executor,
            self._callback_executor.execute,
            "on_tick",
            self._strategy.on_tick,
        )

    async def close(self) -> None:
        """Wait for the active calculation and stop the calculation thread."""
        self._closed = True
        task = self._calculation_task
        if task is not None and not task.done():
            await task
        self._executor.shutdown(wait=True, cancel_futures=True)
