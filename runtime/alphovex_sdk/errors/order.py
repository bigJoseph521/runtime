from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base import SDKError
from ..models.order import OrderSide, OrderType, TimeInForce


class OrderErrorCode(StrEnum):
    """Represent canonical error codes for order-related failures.

    These codes classify issues that can occur while validating,
    constructing, submitting, or managing orders through the SDK.

    The codes are intended to be stable and suitable for
    programmatic error handling.
    """

    # Request / input shape

    ORDER_INVALID_REQUEST = "ORDER_INVALID_REQUEST"
    """Indicate that the order request is malformed or cannot be interpreted."""

    ORDER_MISSING_FIELD = "ORDER_MISSING_FIELD"
    """Indicate that a required order field is missing."""

    ORDER_INVALID_SIDE = "ORDER_INVALID_SIDE"
    """Indicate that the specified order side is invalid or unsupported."""

    ORDER_INVALID_ORDER_TYPE = "ORDER_INVALID_ORDER_TYPE"
    """Indicate that the specified order type is invalid or unsupported."""

    ORDER_INVALID_TIME_IN_FORCE = "ORDER_INVALID_TIME_IN_FORCE"
    """Indicate that the specified time-in-force value is invalid or unsupported."""

    ORDER_INCOMPLETE_INPUT = "ORDER_INCOMPLETE_INPUT"
    """Indicate that the provided order input is incomplete."""

    # Value validation

    ORDER_INVALID_QUANTITY = "ORDER_INVALID_QUANTITY"
    """Indicate that the specified order quantity is invalid."""

    ORDER_INVALID_PRICE = "ORDER_INVALID_PRICE"
    """Indicate that the specified order price is invalid."""

    ORDER_INVALID_STOP_PRICE = "ORDER_INVALID_STOP_PRICE"
    """Indicate that the specified stop price is invalid."""

    ORDER_INVALID_TRAIL_VALUE = "ORDER_INVALID_TRAIL_VALUE"
    """Reserve an error code for future trailing-order value validation."""

    # Parameter relationships

    ORDER_INCOMPATIBLE_PARAMETERS = "ORDER_INCOMPATIBLE_PARAMETERS"
    """Indicate that the provided order parameters are mutually incompatible."""

    ORDER_UNSUPPORTED_CONFIGURATION = "ORDER_UNSUPPORTED_CONFIGURATION"
    """Indicate that the order configuration is valid but not supported."""

    # Execution / lifecycle

    ORDER_REJECTED = "ORDER_REJECTED"
    """Indicate that the order was rejected during processing."""

    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    """Indicate that the requested order could not be found."""

    ORDER_ALREADY_FINALIZED = "ORDER_ALREADY_FINALIZED"
    """Indicate that the order is already finalized and cannot be modified."""

    ORDER_EXPIRED = "ORDER_EXPIRED"
    """Indicate that the order expired before being fully executed."""

    ORDER_OPERATION_FAILED = "ORDER_OPERATION_FAILED"
    """Indicate that an order operation could not be completed."""

    # Risk / account

    ORDER_INSUFFICIENT_BUYING_POWER = "ORDER_INSUFFICIENT_BUYING_POWER"
    """Indicate that the account lacks sufficient buying power."""

    ORDER_POSITION_UNAVAILABLE = "ORDER_POSITION_UNAVAILABLE"
    """Indicate that the required position is unavailable for the request."""

class OrderIntentField(StrEnum):
    """Enumerate public fields of an order intent object."""

    INSTRUMENT_ID = "instrument_id"
    SIDE = "side"
    QUANTITY = "quantity"
    PRICE = "price"
    ORDER_TYPE = "order_type"
    LIMIT_PRICE = "limit_price"
    STOP_PRICE = "stop_price"
    TIME_IN_FORCE = "time_in_force"


class OrderError(SDKError):
    """Serve as the base class for all order-related SDK errors."""


class OrderInvalidRequestError(OrderError):
    """Raise when an order request is malformed or cannot be interpreted.

    Use this error when the overall request shape is invalid and a more
    specific order validation error does not better describe the problem.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_REQUEST,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        reason: str | None = None,
    ) -> "OrderInvalidRequestError":
        """Create an invalid-request error from a general validation reason."""
        details: dict[str, Any] = {}

        if reason is not None:
            details["reason"] = reason

        return cls(
            message="Order request is invalid.",
            details=details or None,
        )


class OrderMissingFieldError(OrderError):
    """Raise when a required field is missing from an order payload.

    Use this error for a missing top-level order field or a missing nested
    field within ``order_intent``.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_MISSING_FIELD,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        field: OrderIntentField,
        nested_field: OrderIntentField | None = None,
    ) -> "OrderMissingFieldError":
        """Create a missing-field error for an order field path."""
        field_path = field.value
        details: dict[str, Any] = {"field": field.value}

        if nested_field is not None:
            field_path = f"{field.value}.{nested_field.value}"
            details["nested_field"] = nested_field.value
            details["field_path"] = field_path
        else:
            details["field_path"] = field_path

        return cls(
            message=f"Required order field '{field_path}' is missing.",
            details=details,
        )


class OrderInvalidSideError(OrderError):
    """Raise when the specified order side is invalid or unsupported.

    Use this error when the provided side does not match the SDK's supported
    ``OrderSide`` values.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_SIDE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        side: str,
        allowed_sides: list[OrderSide] | None = None,
    ) -> "OrderInvalidSideError":
        """Create an invalid-side error for the provided side value."""
        resolved_allowed_sides = allowed_sides or list(OrderSide)

        return cls(
            message="Order side is invalid.",
            details={
                "side": side,
                "allowed_sides": [item.value for item in resolved_allowed_sides],
            },
        )


class OrderInvalidOrderTypeError(OrderError):
    """Raise when the specified order type is invalid or unsupported.

    Use this error when the provided order type does not match the SDK's
    supported ``OrderType`` values.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_ORDER_TYPE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        order_type: object,
    ) -> "OrderInvalidOrderTypeError":
        """Create an invalid-order-type error for the provided value."""
        return cls(
            message="Order type is invalid.",
            details={
                "order_type": order_type,
                "allowed_order_types": [item.value for item in OrderType],
            },
        )


class OrderInvalidTimeInForceError(OrderError):
    """Raise when the specified time-in-force value is invalid or unsupported.

    Use this error when the provided time-in-force value does not match the
    SDK's supported ``TimeInForce`` values.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_TIME_IN_FORCE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        time_in_force: object,
    ) -> "OrderInvalidTimeInForceError":
        """Create an invalid-time-in-force error for the provided value."""
        return cls(
            message="Time in force is invalid.",
            details={
                "time_in_force": time_in_force,
                "allowed_time_in_force": [item.value for item in TimeInForce],
            },
        )


class OrderInvalidQuantityError(OrderError):
    """Raise when the specified order quantity fails basic validation.

    Use this error when quantity is missing, non-numeric, or not greater
    than zero.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_QUANTITY,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        quantity: object,
    ) -> "OrderInvalidQuantityError":
        """Create an invalid-quantity error from the provided quantity."""
        if quantity is None:
            message = "Order quantity is required."
        elif not isinstance(quantity, (int, float)):
            message = "Order quantity must be a number."
        elif quantity <= 0:
            message = "Order quantity must be greater than 0."
        else:
            message = "Order quantity is invalid."

        return cls(
            message=message,
            details={
                "quantity": quantity,
            },
        )


class OrderInvalidPriceError(OrderError):
    """Raise when the specified order price fails basic validation.

    Use this error when price is missing, non-numeric, or not greater
    than zero.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_PRICE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        price: object,
    ) -> "OrderInvalidPriceError":
        """Create an invalid-price error from the provided price."""
        if price is None:
            message = "Order price is required."
        elif not isinstance(price, (int, float)):
            message = "Order price must be a number."
        elif price <= 0:
            message = "Order price must be greater than 0."
        else:
            message = "Order price is invalid."

        return cls(
            message=message,
            details={"price": price},
        )


class OrderInvalidStopPriceError(OrderError):
    """Raise when the specified stop price fails basic validation.

    Use this error when stop price is missing, non-numeric, or not greater
    than zero in a context where a stop price is required.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_STOP_PRICE,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        stop_price: object,
    ) -> "OrderInvalidStopPriceError":
        """Create an invalid-stop-price error from the provided stop price."""
        if stop_price is None:
            message = "Stop price is required."
        elif not isinstance(stop_price, (int, float)):
            message = "Stop price must be a number."
        elif stop_price <= 0:
            message = "Stop price must be greater than 0."
        else:
            message = "Stop price is invalid."

        return cls(
            message=message,
            details={"stop_price": stop_price},
        )


class OrderInvalidTrailValueError(OrderError):
    """Reserve an error type for future trailing-order validation.

    This error is intentionally present for forward compatibility, but
    trailing order parameters are not yet supported by the SDK.
    """

    def __init__(
        self,
        message: str = "Trailing order values are not supported.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INVALID_TRAIL_VALUE,
            details=details,
        )

    @classmethod
    def create(cls, *args: Any, **kwargs: Any) -> "OrderInvalidTrailValueError":
        """Reject creation because trailing-order validation is not implemented."""
        raise NotImplementedError(
            "Trailing order validation is not supported yet."
        )


class OrderIncompatibleParametersError(OrderError):
    """Raise when valid parameters form an invalid combination.

    Use this error when individual parameter values are valid on their own,
    but the combination of those parameters is not logically allowed.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INCOMPATIBLE_PARAMETERS,
            details=details,
        )

    @classmethod
    def create(
        cls,
        *,
        parameters: list[OrderIntentField],
        reason: str | None = None,
    ) -> "OrderIncompatibleParametersError":
        """Create an incompatible-parameters error for conflicting fields."""
        details: dict[str, Any] = {
            "parameters": parameters,
        }

        if reason is not None:
            details["reason"] = reason

        return cls(
            message="Order parameters are incompatible.",
            details=details,
        )


class OrderUnsupportedConfigurationError(OrderError):
    """Raise when an order configuration is valid but not supported.

    This error is produced by the SDK or runtime when the provided order
    configuration is logically valid, but cannot be executed due to platform,
    broker, or SDK capability limitations.

    Users may catch and inspect this error, but should not construct it.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_UNSUPPORTED_CONFIGURATION,
            details=details,
        )


class OrderRejectedError(OrderError):
    """Raise when an order is rejected during execution.

    This error represents a rejection returned by platfrom, broker, 
    or exchange after the order has passed validation.

    Users may catch this error to handle execution failures in strategy logic.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_REJECTED,
            details=details,
        )


class OrderNotFoundError(OrderError):
    """Raise when an order is rejected during execution.

    This error represents a rejection returned by the runtime, OMS, risk
    engine, broker, or exchange after the order has passed validation.

    Users may catch this error to handle execution failures in strategy logic.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_NOT_FOUND,
            details=details,
        )


class OrderAlreadyFinalizedError(OrderError):
    """Raise when an order is already finalized and cannot be modified.

    This error occurs when an operation targets an order that is in a
    terminal state, such as filled, cancelled, rejected, or expired.

    Users may catch this error to prevent invalid state transitions.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_ALREADY_FINALIZED,
            details=details,
        )

class OrderOperationFailedError(OrderError):
    """Raise when an order is already finalized and cannot be modified.

    This error occurs when an operation targets an order that is in a
    terminal state, such as filled, cancelled, rejected, or expired.

    Users may catch this error to prevent invalid state transitions.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_OPERATION_FAILED,
            details=details,
        )

class OrderExpiredError(OrderError):
    """Raise when an order expires before full execution.

    This error occurs when an order reaches its expiration condition,
    typically defined by time-in-force, before being fully filled.

    Users may catch this error to handle unfilled or partially filled
    orders that expire.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_EXPIRED,
            details=details,
        )


class OrderInsufficientBuyingPowerError(OrderError):
    """Raise when the account lacks sufficient buying power.

    This error occurs when the account does not have enough available
    funds or margin to accept or execute the requested order.

    Users may catch this error to adjust position sizing or risk.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_INSUFFICIENT_BUYING_POWER,
            details=details,
        )


class OrderPositionUnavailableError(OrderError):
    """Raise when the account lacks sufficient buying power.

    This error occurs when the account does not have enough available
    funds or margin to accept or execute the requested order.

    Users may catch this error to adjust position sizing or risk.
    """

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=OrderErrorCode.ORDER_POSITION_UNAVAILABLE,
            details=details,
        )