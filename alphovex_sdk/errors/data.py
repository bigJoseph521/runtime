from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base import SDKError
from ..typedefs import Timeframe, Symbol, Timestamp

class DataErrorCode(StrEnum):
    """
    Error codes for data-related failures.

    Each code represents a category of data issues that may occur during
    data requests. Use these codes to handle errors and define fallback
    behavior in your strategy logic.
    """

    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    DATA_STALE = "DATA_STALE"
    DATA_ACCESS_DENIED = "DATA_ACCESS_DENIED"
    DATA_RATE_LIMITED = "DATA_RATE_LIMITED"
    DATA_TIMEOUT = "DATA_TIMEOUT"
    DATA_INCOMPLETE = "DATA_INCOMPLETE"
    DATA_INVALID_RANGE = "DATA_INVALID_RANGE"
    DATA_UNSUPPORTED_TIMEFRAME = "DATA_UNSUPPORTED_TIMEFRAME"

class DataResource(StrEnum):
    BAR = "bar"
    QUOTE = "quote"
    TICK = "tick"
    POSITION = "position"
    PORTFOLIO = "portfolio"
    BALANCE = "balance"
    ORDER = "order"
    MARKET_SESSION = "market session"

class DataError(SDKError):
    """Base class for all data-related SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        code: DataErrorCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a data-related SDK error.

        Parameters
        ----------
        message:
            Human-readable error message.
        code:
            Stable SDK-facing data error code.
        details:
            Optional structured metadata describing the error context.
        """
        super().__init__(message=message, code=code, details=details)

class DataNotFoundError(DataError):
    """
    Raised when the requested data does not exist.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_NOT_FOUND,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        resource: DataResource,
        symbol: Symbol | None = None,
        timeframe: Timeframe | None = None,
        start: Timestamp | None = None,
        end: Timestamp | None = None,
    ) -> "DataNotFoundError":
        """
        Create an error for requested data that was not found.
        """
        details: dict[str, Any] = {"resource": resource.value}

        if symbol is not None:
            details["symbol"] = symbol
        if timeframe is not None:
            details["timeframe"] = timeframe
        if start is not None:
            details["start"] = start
        if end is not None:
            details["end"] = end

        return cls(
            message=f"No {resource.value} data found.",
            details=details,
        )

class DataUnavailableError(DataError):
    """
    Raised when requested data is temporarily unavailable.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_UNAVAILABLE,
            details=details,
        )

class DataStaleError(DataError):
    """
    Raised when requested data is older than the required freshness.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_STALE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        resource: DataResource,
        last_updated: Timestamp,
        max_age_seconds: int | None = None,
        symbol: Symbol | None = None,
        timeframe: Timeframe | None = None,
    ) -> "DataStaleError":
        details: dict[str, Any] = {
            "resource": resource.value,
            "last_updated": last_updated,
        }

        if max_age_seconds is not None:
            details["max_age_seconds"] = max_age_seconds
        if symbol is not None:
            details["symbol"] = symbol
        if timeframe is not None:
            details["timeframe"] = timeframe

        return cls(
            message=f"{resource.value.capitalize()} data is stale.",
            details=details,
        )

class DataAccessError(DataError):
    """
    Raised when access to requested data is denied or restricted.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_ACCESS_DENIED,
            details=details,
        )

class DataRateLimitedError(DataError):
    """
    Raised when data requests exceed allowed rate limits.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_RATE_LIMITED,
            details=details,
        )

class DataTimeoutError(DataError):
    """
    Raised when a data request does not complete within the expected time.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_TIMEOUT,
            details=details,
        )

class DataIncompleteError(DataError):
    """
    Raised when returned data is incomplete.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_INCOMPLETE,
            details=details,
        )

class DataInvalidRangeError(DataError):
    """
    Raised when the requested data range is not supported.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_INVALID_RANGE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        resource: DataResource,
        start: Timestamp | None = None,
        end: Timestamp | None = None,
        timeframe: Timeframe | None = None,
        reason: str | None = None,
    ) -> "DataInvalidRangeError":
        details: dict[str, Any] = {"resource": resource.value}

        if start is not None:
            details["start"] = start
        if end is not None:
            details["end"] = end
        if timeframe is not None:
            details["timeframe"] = timeframe
        if reason is not None:
            details["reason"] = reason

        return cls(
            message=f"Requested {resource.value} data range is not supported.",
            details=details,
        )

class DataUnsupportedTimeframeError(DataError):
    """
    Raised when the requested timeframe is not supported for the data.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=DataErrorCode.DATA_UNSUPPORTED_TIMEFRAME,
            details=details,
        )