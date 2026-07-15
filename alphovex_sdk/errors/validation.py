from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base import SDKError


class ValidationErrorCode(StrEnum):
    """User-facing validation error codes for the Alphovex SDK.

    These codes classify validation failures in a consistent and
    machine-readable way. They are intended for strategy developers and
    external SDK consumers, and must remain stable and independent from
    internal platform or runtime error definitions.

    Detailed context about a validation failure should be provided through
    the error ``details`` field rather than by creating overly specific
    error codes.
    """

    # Core
    VALIDATION_MISSING_PARAMETER = "VALIDATION_MISSING_PARAMETER"
    VALIDATION_INVALID_TYPE = "VALIDATION_INVALID_TYPE"
    VALIDATION_INVALID_VALUE = "VALIDATION_INVALID_VALUE"
    VALIDATION_OUT_OF_RANGE = "VALIDATION_OUT_OF_RANGE"
    VALIDATION_INVALID_STATE = "VALIDATION_INVALID_STATE"

    # Structural
    VALIDATION_SCHEMA_VIOLATION = "VALIDATION_SCHEMA_VIOLATION"
    VALIDATION_INCOMPLETE_INPUT = "VALIDATION_INCOMPLETE_INPUT"

    # Semantic / relational
    VALIDATION_CONSTRAINT_VIOLATION = "VALIDATION_CONSTRAINT_VIOLATION"
    VALIDATION_INCOMPATIBLE_PARAMETERS = "VALIDATION_INCOMPATIBLE_PARAMETERS"

    # Format / support
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_UNSUPPORTED_VALUE = "VALIDATION_UNSUPPORTED_VALUE"

    # Optional / advanced
    VALIDATION_DUPLICATE_VALUE = "VALIDATION_DUPLICATE_VALUE"
    VALIDATION_INVALID_PRECISION = "VALIDATION_INVALID_PRECISION"


class ValidationError(SDKError):
    """Base class for validation-related SDK errors.

    This error is raised when user input or SDK usage violates expected
    constraints, type requirements, or domain invariants.

    Validation errors are safe to expose to strategy developers and should
    provide clear, actionable feedback. Each error includes a
    ``ValidationErrorCode`` that categorizes the failure in a consistent,
    machine-readable way.

    Parameters
    ----------
    message:
        Human-readable description of the validation failure.
    code:
        Validation error code categorizing the failure.
    details:
        Optional structured metadata providing additional context.
    """

    def __init__(
        self,
        message: str,
        *,
        code: ValidationErrorCode,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a validation error."""
        super().__init__(
            message=message,
            code=code,
            details=details,
        )


class MissingParameterError(ValidationError):
    """Raised when a required parameter is not provided.

    Preferred usage is ``MissingParameterError.create(...)`` for
    consistent messages and detail payloads. Direct instantiation remains
    available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a missing-parameter validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_MISSING_PARAMETER,
            details=details,
        )

    @classmethod
    def create(
        cls,
        parameter: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> "MissingParameterError":
        """Create an error for a missing required parameter."""
        payload: dict[str, Any] = {"parameter": parameter}
        if details:
            payload.update(details)

        return cls(
            message=f"Missing required parameter: {parameter}.",
            details=payload,
        )


class InvalidTypeError(ValidationError):
    """Raised when a provided value has an incorrect type.

    Preferred usage is ``InvalidTypeError.create(...)`` for
    consistent messages and detail payloads. Direct instantiation remains
    available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an invalid-type validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INVALID_TYPE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        parameter: str,
        expected: str,
        actual: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> "InvalidTypeError":
        """Create an error for a parameter with an invalid type."""
        payload: dict[str, Any] = {
            "parameter": parameter,
            "expected": expected,
            "actual": actual,
        }
        if details:
            payload.update(details)

        return cls(
            message=(
                f"Invalid type for parameter '{parameter}': "
                f"expected {expected}, got {actual}."
            ),
            details=payload,
        )


class InvalidValueError(ValidationError):
    """Raised when a provided value is invalid despite having the correct type."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an invalid-value validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INVALID_VALUE,
            details=details,
        )


class OutOfRangeError(ValidationError):
    """Raised when a provided value is outside the allowed range.

    Preferred usage is ``OutOfRangeError.create(...)`` for
    consistent messages and detail payloads. Direct instantiation remains
    available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an out-of-range validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_OUT_OF_RANGE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        parameter: str,
        actual: Any,
        *,
        minimum: Any | None = None,
        maximum: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> "OutOfRangeError":
        """Create an error for a parameter whose value is out of range."""
        payload: dict[str, Any] = {
            "parameter": parameter,
            "actual": actual,
        }
        if minimum is not None:
            payload["minimum"] = minimum
        if maximum is not None:
            payload["maximum"] = maximum
        if details:
            payload.update(details)

        if minimum is not None and maximum is not None:
            message = (
                f"Parameter '{parameter}' is out of range: "
                f"expected between {minimum} and {maximum}, got {actual}."
            )
        elif minimum is not None:
            message = (
                f"Parameter '{parameter}' is out of range: "
                f"expected >= {minimum}, got {actual}."
            )
        elif maximum is not None:
            message = (
                f"Parameter '{parameter}' is out of range: "
                f"expected <= {maximum}, got {actual}."
            )
        else:
            message = f"Parameter '{parameter}' is out of range: got {actual}."

        return cls(
            message=message,
            details=payload,
        )


class InvalidStateError(ValidationError):
    """Raised when an operation is not allowed in the current state.

    Preferred usage is ``InvalidStateError.for_state(...)`` for
    consistent messages and detail payloads. Direct instantiation remains
    available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an invalid-state validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INVALID_STATE,
            details=details,
        )

    @classmethod
    def for_state(
        cls,
        state: str,
        *,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "InvalidStateError":
        """Create an error for an operation attempted in an invalid state."""
        payload: dict[str, Any] = {"state": state}
        if operation is not None:
            payload["operation"] = operation
        if details:
            payload.update(details)

        if operation is not None:
            message = (
                f"Operation '{operation}' is not allowed in the current "
                f"state: {state}."
            )
        else:
            message = f"Operation is not allowed in the current state: {state}."

        return cls(
            message=message,
            details=payload,
        )


class SchemaViolationError(ValidationError):
    """Raised when input data does not conform to the expected schema."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a schema-violation validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_SCHEMA_VIOLATION,
            details=details,
        )


class IncompleteInputError(ValidationError):
    """Raised when input is partially provided but missing required components."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an incomplete-input validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INCOMPLETE_INPUT,
            details=details,
        )


class ConstraintViolationError(ValidationError):
    """Raised when a logical or relational constraint is violated."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a constraint-violation validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_CONSTRAINT_VIOLATION,
            details=details,
        )


class IncompatibleParametersError(ValidationError):
    """Raised when provided parameters cannot be used together.

    Preferred usage is ``IncompatibleParametersError.for_parameters(...)``
    for consistent messages and detail payloads. Direct instantiation
    remains available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an incompatible-parameters validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INCOMPATIBLE_PARAMETERS,
            details=details,
        )

    @classmethod
    def for_parameters(
        cls,
        parameters: list[str],
        *,
        details: dict[str, Any] | None = None,
    ) -> "IncompatibleParametersError":
        """Create an error for incompatible parameters."""
        payload: dict[str, Any] = {"parameters": parameters}
        if details:
            payload.update(details)

        joined = ", ".join(parameters)
        return cls(
            message=f"Incompatible parameters provided: {joined}.",
            details=payload,
        )


class InvalidFormatError(ValidationError):
    """Raised when a value has the correct type but an invalid format.

    Preferred usage is ``InvalidFormatError.create(...)`` for
    consistent messages and detail payloads. Direct instantiation remains
    available for advanced cases.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an invalid-format validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INVALID_FORMAT,
            details=details,
        )

    @classmethod
    def create(
        cls,
        parameter: str,
        expected_format: str,
        actual: Any,
        *,
        details: dict[str, Any] | None = None,
    ) -> "InvalidFormatError":
        """Create an error for a parameter with an invalid format."""
        payload: dict[str, Any] = {
            "parameter": parameter,
            "expected_format": expected_format,
            "actual": actual,
        }
        if details:
            payload.update(details)

        return cls(
            message=(
                f"Invalid format for parameter '{parameter}': "
                f"expected {expected_format}."
            ),
            details=payload,
        )


class UnsupportedValueError(ValidationError):
    """Raised when a provided value is not supported."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an unsupported-value validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_UNSUPPORTED_VALUE,
            details=details,
        )


class DuplicateValueError(ValidationError):
    """Raised when a duplicate value is detected where uniqueness is required."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a duplicate-value validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_DUPLICATE_VALUE,
            details=details,
        )


class InvalidPrecisionError(ValidationError):
    """Raised when a numeric value does not satisfy required precision rules."""

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an invalid-precision validation error."""
        super().__init__(
            message=message,
            code=ValidationErrorCode.VALIDATION_INVALID_PRECISION,
            details=details,
        )