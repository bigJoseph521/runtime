from __future__ import annotations

from email import message_from_string
import math

from ..errors import InvalidValueError, ConstraintViolationError, InvalidPrecisionError

def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Return numerator / denominator, or default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator

def is_close(
    a: float,
    b: float,
    #,
    rel_tol: float = 1e-9,
    abs_tol: float = 1e-12,
) -> bool:
    """Return True if two numbers are approximately equal."""
    if rel_tol < 0:
        raise InvalidValueError(
            "rel_tol must be non-negative.",
            details={"parameter": "rel_tol", "actual": rel_tol},
        )
    if abs_tol < 0:
        raise InvalidValueError(
            "abs_tol must be non-negative.",
            details={"parameter": "abs_tol", "actual": abs_tol},
        )
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to the inclusive range [min_val, max_val]."""
    if min_val > max_val:
        raise ConstraintViolationError(
            message="min_val must be less than or equal to max_val.",
            details={
                "parameter": "min_val", 
                "actual": min_val, 
                "max_val": max_val
            },
        )
    return max(min_val, min(value, max_val))

def normalize(value: float, min_value: float, max_value: float) -> float:
    """Normalize value to the range [0, 1] using (value - min_value) / (max_value - min_value)."""
    if min_value == max_value:
        raise InvalidValueError(
            message="min_value and max_value must not be equal.",
            details={
                "min_value": min_value,
                "max_value": max_value,
            },
        )
    return (value - min_value) / (max_value - min_value)


def to_percent(value: float) -> float:
    """Convert ratio to percentage."""
    return value * 100.0

def from_percent(percent: float) -> float:
    """Convert percentage to ratio."""
    return percent / 100.0

def round_to(value: float, decimals: int) -> float:
    """Round value to a fixed number of decimal places."""
    if decimals < 0:
        raise InvalidPrecisionError(
            "decimals must be greater than or equal to zero.",
            details={"parameter": "decimals", "actual": decimals},
        )
    return round(value, decimals)

def is_finite(value: float) -> bool:
    """Return True if value is finite."""
    return math.isfinite(value)
