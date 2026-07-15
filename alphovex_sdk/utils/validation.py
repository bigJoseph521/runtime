"""Validation helpers for common SDK input checks.

This module provides small, reusable functions for validating values used
across the SDK. These helpers keep validation logic consistent and raise
structured SDK validation errors when inputs are invalid.

The functions in this module are intentionally stateless. They validate
inputs, return the original value when valid, and raise an appropriate
error when invalid.
"""
from __future__ import annotations

import re
from enum import StrEnum, Enum
from typing import Any
from numbers import Real
from collections.abc import Collection

from ..typedefs import Symbol
from ..errors import (
    ConstraintViolationError,
    InvalidFormatError,
    InvalidTypeError,
    InvalidValueError,
    MissingParameterError,
    OutOfRangeError,
)


def require_not_none(value: Any, *, field_name: str) -> Any:
    """Raise a MissingParameterError if the value is None."""
    if value is None:
        raise MissingParameterError.create(field_name)
    return value

def require_type(
    value: Any,
    expected_type: type[Any] | tuple[type[Any], ...],
    *,
    field_name: str,
) -> Any:
    """Raise an InvalidTypeError if the value is not of the expected type."""
    if not isinstance(value, expected_type):
        if isinstance(expected_type, tuple):
            expected_label = ", ".join(t.__name__ for t in expected_type)
        else:
            expected_label = expected_type.__name__
        raise InvalidTypeError.create(
            parameter=field_name, 
            expected=expected_label,
            actual=type(value).__name__
        )
    return value

def require_positive(value: Real, *, field_name: str) -> Real:
    require_type(value, Real, field_name=field_name)
    """Raise an InvalidValueError if the value is less than or equal to zero."""
    if value <= 0:
        raise InvalidValueError(
            message=f"Parameter '{field_name}' must be greater than 0.",
            details={
                "parameter": field_name,
                "actual": value,
                "constraint": "value > 0",
            },
        )
    return value

def require_non_empty(value: Any, *, field_name: str) -> Any:
    """Raise an InvalidValueError if the value is empty."""
    require_not_none(value, field_name=field_name)

    if isinstance(value, str):
        if value.strip() == "":
            raise InvalidValueError(
                message = f"Parameter '{field_name}' must not be empty.",
                details = {"parameter": field_name, "actual": value},
            )
        return value
    
    if isinstance(value, Collection):
        if len(value) == 0:
            raise InvalidValueError(
                message=f"Parameter '{field_name}' must not be empty.",
                details={"parameter": field_name, "actual": value},
            )
        return value

    raise InvalidTypeError.create(
        parameter=field_name,
        expected="non-empty str or collection",
        actual=type(value).__name__,
    )

def require_in(value: Any, *, allowed_values: Collection[Any], field_name: str) -> Any:
    """Raise an InvalidValueError if the value is not in the allowed values."""
    require_non_empty(allowed_values, field_name="allowed_values")
    if value not in allowed_values:
        raise InvalidValueError(
            message = (
                f"Parameter '{field_name}' must be one of "
                f"{list(allowed_values)!r}; got {value!r}."
            ),
            details = {
                "parameter": field_name,
                "actual": value,
                "allowed_values": list(allowed_values),
            }
        )
    return value

def require_range(
    value: Real,
    *,
    field_name: str,
    minimum: Real | None = None,
    maximum: Real | None = None,
) -> Real:
    """Raise an OutOfRangeError if the value is not in the range."""
    require_type(value, Real, field_name=field_name)

    if minimum is None and maximum is None:
        raise ConstraintViolationError(
            message = "Range validation requires at least one bound.",
            details = {"parameter": field_name}
        )
    
    if minimum is not None and value < minimum:
        raise OutOfRangeError.create(
            parameter = field_name,
            actual = value,
            minimum = minimum,
            maximum = maximum,
        )
    
    if maximum is not None and value > maximum:
        raise OutOfRangeError.create(
            parameter = field_name,
            actual = value,
            minimum = minimum,
            maximum = maximum,
        )
    
    return value

def require_enum(value: Any, *, enum_cls: type[Enum], field_name: str) -> Any:
    """Raise an InvalidTypeError if the value is not an instance of the enum class."""
    if not isinstance(value, enum_cls):
        allowed_values = [member.name for member in enum_cls]
        raise InvalidTypeError.create(
            parameter=field_name,
            expected=f"{enum_cls.__name__} ({', '.join(allowed_values)})",
            actual=type(value).__name__,
        )
    return value

def normalize_symbol(symbol: Symbol) -> Symbol:
    """
    Raise an InvalidFormatError if the symbol is not a valid trading symbol 
    (after stripping, uppercasing, and format validation).
    """
    require_type(symbol, str, field_name="symbol")
    normalized = symbol.strip().upper()

    if not re.match(r"^[A-Z0-9.\-]+$", normalized):
        raise InvalidFormatError.create(
            parameter="symbol",
            expected_format="uppercase alphanumeric symbol (A-Z, 0-9, ., -)",
            actual=symbol,
        )
    
    return normalized
    




