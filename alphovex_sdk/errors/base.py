from __future__ import annotations

from enum import StrEnum
from typing import Any

class SDKError(Exception):
    """
    Base class for errors raised by the Alphovex SDK.

    Represents a failure with a stable machine-readable code, a human-readable
    message, and optional structured details for logging or debugging. Catch
    this type to handle SDK-related failures generically in strategy or host
    code; read fields through ``message()``, ``code()``, and ``details()``.
    """

    def __init__(
        self, 
        message: str,
        *,
        code: StrEnum,
        details: dict[str, Any] | None  = None
    ) -> None:
        """
        Initialize the SDK error.

        Parameters
        ----------
        message:
            Human-readable error message.
        code:
            Optional predefined StrEnum error code.
        details:
            Optional structured metadata describing the error context.
        """
        super().__init__(message)
        
        if code is None and not isinstance(code, StrEnum):
            raise TypeError("Code must be an instance of StrEnum or None")
        
        if details is not None and not isinstance(details, dict):
            raise TypeError("Details must be a dictionary or None")
        
        self._code = code
        self._message = message
        self._details = details.copy() if details is not None else None

    def message(self) -> str:
        """Retunr the human-readable error message."""
        return self._message
    
    def code(self) -> StrEnum:
        """Return the predefined StrEnum error code."""
        return self._code
    
    def details(self) -> dict[str, Any] | None:
        """Return the structured metadata describing the error context."""
        return self._details.copy() if self._details is not None else None
    
    def to_dict(self) -> dict[str, Any]:
        """
        Return a JSON-friendly representation of the error

        The code is serialized using 'code.value' so downstream systems can
        safely consume the normalized string form.
        """
        return {
            "type": type(self).__name__,
            "message": self.message(),
            "code": self.code().value,
            "details": self.details() if self.details() is not None else None,
        }
    
    def __str__(self) -> str:
        """ Return the user-friendly string form of the error"""
        return f"[{self.code().value}] {self.message()}"

    def __repr__(self) -> str:
        """Return the developer-friendly representation of the error"""
        return (
            f"{type(self).__name__}("
            f"message={self.message()!r}, "
            f"code={self.code()!r}, "
            f"details={self.details()!r})"
        )