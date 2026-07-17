from __future__ import annotations

from dataclasses import dataclass
import linecache
from pathlib import Path
import threading
import time
import traceback
from types import FrameType, TracebackType

from application.context.logging_context import RuntimeLoggingContext


@dataclass(slots=True)
class _ErrorWindow:
    started_at: float
    emitted_count: int = 0
    suppressed_count: int = 0


class StrategyErrorReporter:
    """Report user-code failures with source location and bounded logging."""

    def __init__(
        self,
        logger: RuntimeLoggingContext,
        strategy_root: str | Path,
        *,
        window_seconds: float = 60.0,
        max_logs_per_window: int = 5,
    ) -> None:
        self._logger = logger
        self._strategy_root = Path(strategy_root).resolve()
        self._window_seconds = window_seconds
        self._max_logs_per_window = max_logs_per_window
        self._windows: dict[tuple[str, str, str | None, int | None, str], _ErrorWindow] = {}
        self._lock = threading.Lock()

    def report(self, callback_name: str, error: Exception) -> None:
        location = self._find_strategy_error_location(error.__traceback__)
        file_name: str | None = None
        row: int | None = None
        function: str | None = None
        code: str | None = None

        if location is not None:
            frame, row = location
            file_path = Path(frame.f_code.co_filename).resolve()
            try:
                file_name = str(file_path.relative_to(self._strategy_root))
            except ValueError:
                file_name = file_path.name
            function = frame.f_code.co_name
            code = linecache.getline(str(file_path), row).strip() or None

        fingerprint = (
            callback_name,
            type(error).__name__,
            file_name,
            row,
            str(error),
        )
        emit, occurrence_count, suppressed_count = self._record_occurrence(fingerprint)
        if not emit:
            return

        fields = {
            "source": "USER_STRATEGY",
            "callback": callback_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "file": file_name,
            "row": row,
            "function": function,
            "code": code,
            "occurrence_count": occurrence_count,
        }
        if suppressed_count:
            fields["previously_suppressed_count"] = suppressed_count

        self._logger.error(
            message="Strategy callback failed",
            **fields,
        )
        self._logger.platform_error(
            message="User strategy callback failed",
            traceback="".join(
                traceback.format_exception(
                    type(error),
                    error,
                    error.__traceback__,
                )
            ),
            **fields,
        )

    def _record_occurrence(
        self,
        fingerprint: tuple[str, str, str | None, int | None, str],
    ) -> tuple[bool, int, int]:
        now = time.monotonic()
        with self._lock:
            window = self._windows.get(fingerprint)
            if window is None:
                window = _ErrorWindow(started_at=now)
                self._windows[fingerprint] = window
            elif now - window.started_at >= self._window_seconds:
                suppressed = window.suppressed_count
                window = _ErrorWindow(started_at=now)
                self._windows[fingerprint] = window
                window.emitted_count = 1
                return True, 1, suppressed

            occurrence_count = window.emitted_count + window.suppressed_count + 1
            if window.emitted_count >= self._max_logs_per_window:
                window.suppressed_count += 1
                return False, occurrence_count, 0

            window.emitted_count += 1
            return True, occurrence_count, 0

    def _find_strategy_error_location(
        self,
        traceback_value: TracebackType | None,
    ) -> tuple[FrameType, int] | None:
        """Return the innermost traceback frame inside user strategy code."""
        selected: tuple[FrameType, int] | None = None

        while traceback_value is not None:
            frame = traceback_value.tb_frame
            file_path = Path(frame.f_code.co_filename).resolve()
            if file_path.is_relative_to(self._strategy_root):
                selected = (frame, traceback_value.tb_lineno)
            traceback_value = traceback_value.tb_next

        return selected
