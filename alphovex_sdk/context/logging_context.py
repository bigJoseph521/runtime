from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LoggingContext(ABC):
    """
    Provides logging methods for strategy code.

    This interface allows a strategy to record messages while it runs.
    Logging can be used to inspect decisions, track important events,
    report unexpected situations, and help with debugging.

    Use this context when you want to:
    - trace strategy behavior step by step
    - record signal generation or order decisions
    - warn about unusual conditions
    - report errors that affect strategy logic

    Notes
    -----
    - Logging methods do not return a value.
    - Extra keyword arguments can be used to attach additional context
      such as symbols, prices, signals, or parameter values.
    - Logging supports observation and debugging, not replace
      strategy state or business logic.
    """

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """
        Log a debug message.

        Debug messages are useful for detailed inspection of strategy behavior.
        They are typically used for development, troubleshooting, and tracing
        step-by-step decisions.

        Parameters
        ----------
        message:
            Main log message.
        **kwargs:
            Additional context values to include with the log entry.

        Examples
        --------
        Log a simple debug message:

        >>> ctx.logging.debug("Checking entry conditions")

        Log a debug message with extra context:

        >>> ctx.logging.debug(
        ...     "Momentum signal calculated",
        ...     symbol="AAPL",
        ...     signal=0.83,
        ...     lookback=20,
        ... )
        """
        ...

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """
        Log an informational message.

        Informational messages are useful for recording normal strategy events
        such as state changes, entry signals, exits, or important milestones
        during execution.

        Parameters
        ----------
        message:
            Main log message.
        **kwargs:
            Additional context values to include with the log entry.

        Examples
        --------
        Log a simple informational message:

        >>> ctx.logging.info("Strategy initialized")

        Log an informational message with extra context:

        >>> ctx.logging.info(
        ...     "Submitting buy signal",
        ...     symbol="MSFT",
        ...     quantity=10,
        ...     price=412.50,
        ... )
        """
        ...

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """
        Log a warning message.

        Warning messages are useful when strategy code encounters an unusual
        or potentially problematic condition but can still continue running.

        Parameters
        ----------
        message:
            Main log message.
        **kwargs:
            Additional context values to include with the log entry.

        Examples
        --------
        Log a warning about an unusual situation:

        >>> ctx.logging.warning("Price data appears delayed")

        Log a warning with extra context:

        >>> ctx.logging.warning(
        ...     "Skipping signal because volume is too low",
        ...     symbol="TSLA",
        ...     volume=1200,
        ...     minimum_volume=5000,
        ... )
        """
        ...

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """
        Log an error message.

        Error messages are useful when strategy code encounters a failure or
        invalid condition that affects expected behavior.

        Parameters
        ----------
        message:
            Main log message.
        **kwargs:
            Additional context values to include with the log entry.

        Examples
        --------
        Log an error message:

        >>> ctx.logging.error("Failed to calculate position size")

        Log an error message with extra context:

        >>> ctx.logging.error(
        ...     "Order submission failed",
        ...     symbol="NVDA",
        ...     side="buy",
        ...     quantity=5,
        ... )
        """
        ...
