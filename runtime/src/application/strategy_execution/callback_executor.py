from __future__ import annotations

from collections.abc import Callable
from typing import Any

from application.strategy_execution.error_reporter import StrategyErrorReporter


class StrategyCallbackExecutor:
    """Execute user callbacks behind the runtime's exception boundary."""

    def __init__(self, error_reporter: StrategyErrorReporter) -> None:
        self._error_reporter = error_reporter

    def execute(
        self,
        callback_name: str,
        callback: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        try:
            callback(*args, **kwargs)
            return True
        except Exception as error:
            self._error_reporter.report(
                callback_name=callback_name,
                error=error,
            )
            return False
