from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..typedefs import (
    OrderId,
    PriceValue,
    QuantityValue,
    Symbol,
    Timestamp,
)
from ..utils import safe_div


class OrderSide(StrEnum):
    """
    Define the supported sides of an order.

    Members
    -------
    BUY
        Submit an order to purchase an asset.
    SELL
        Submit an order to sell an asset.
    """

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """
    Define the order types recognized by the SDK.

    ``MARKET``, ``LIMIT``, ``STOP``, and ``STOP_LIMIT`` are available for
    strategy order submission. Other members are reserved for future platform
    support.

    Members
    -------
    MARKET
        Execute the order at the best available market price.
    LIMIT
        Execute the order only at the specified limit price or better.
    STOP
        Activate the order after the specified stop price is reached.
    STOP_LIMIT
        Activate a limit order after the specified stop price is reached.
    TAKE_PROFIT
        Reserved order type for closing a position at a profit target.
    TRAILING_STOP
        Reserved order type whose stop price follows favorable market
        movement.
    """

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"


class TimeInForce(StrEnum):
    """
    Define how long an order remains active.

    Availability depends on the connected broker, asset class, order type,
    and trading session.

    Members
    -------
    DAY
        Keep the order active until the end of the current trading day.
    GTC
        Keep the order active until it is filled or explicitly cancelled.
    IOC
        Fill as much as possible immediately and cancel any remaining
        quantity.
    FOK
        Fill the entire order immediately or cancel it completely.
    GTD
        Keep the order active until a specified expiration date.
    AT_THE_OPEN
        Execute the order at or near the market open.
    AT_THE_CLOSE
        Execute the order at or near the market close.
    GOOD_TILL_EXPIRED
        Keep the order active until its configured expiration condition.
    GOOD_TILL_TIME
        Keep the order active until a specified timestamp.
    GOOD_TILL_TIME_NANO
        Keep the order active until a nanosecond-precision timestamp.
    """

    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
    GTD = "gtd"
    AT_THE_OPEN = "at_the_open"
    AT_THE_CLOSE = "at_the_close"
    GOOD_TILL_EXPIRED = "good_till_expired"
    GOOD_TILL_TIME = "good_till_time"
    GOOD_TILL_TIME_NANO = "good_till_time_nano"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    """
    Represent validated inputs for constructing an order.

    An order intent describes what a strategy wants to submit. It does not
    represent broker acceptance, execution, or fill state.

    Attributes
    ----------
    symbol
        Symbol of the asset to buy or sell.
    side
        Direction of the order.
    quantity
        Requested order quantity.
    price
        Reference or working price used during order validation.
    order_type
        Execution behavior requested for the order.
    limit_price
        Limit price for a limit order, or ``None`` when not applicable.
    stop_price
        Trigger price for a stop order, or ``None`` when not applicable.
    time_in_force
        Policy controlling how long the order remains active, or ``None`` to
        use the platform default.

    Notes
    -----
    Instances are immutable after construction.

    The current validation rules require ``limit_price`` only for
    ``OrderType.LIMIT`` and ``stop_price`` only for ``OrderType.STOP``.

    Raises
    ------
    ValueError
        Raised when required values are missing, numeric values are not
        positive, enum values are invalid, or order parameters are
        incompatible.
    """

    symbol: Symbol
    side: OrderSide
    quantity: QuantityValue
    price: PriceValue
    order_type: OrderType
    limit_price: PriceValue | None = None
    stop_price: PriceValue | None = None
    time_in_force: TimeInForce | None = None

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the order intent.

        Returns
        -------
        str
            String containing all order-intent fields.
        """
        return (
            f"OrderIntent(symbol={self.symbol!r}, "
            f"side={self.side!r}, "
            f"quantity={self.quantity!r}, "
            f"price={self.price!r}, "
            f"order_type={self.order_type!r}, "
            f"limit_price={self.limit_price!r}, "
            f"stop_price={self.stop_price!r}, "
            f"time_in_force={self.time_in_force!r})"
        )

    def __post_init__(self) -> None:
        """
        Validate the order-intent fields after initialization.

        Raises
        ------
        ValueError
            Raised when a required field is missing, an enum value is
            unsupported, a price is not positive, or price fields conflict
            with the selected order type.
        """
        if self.side is None:
            raise ValueError("Side is required")
        if self.side not in OrderSide:
            raise ValueError(f"Invalid side: {self.side}")

        if self.quantity is None:
            raise ValueError("Quantity is required")

        if self.price is None:
            raise ValueError("Price is required")
        if self.price <= 0:
            raise ValueError("Price must be greater than 0")

        if self.order_type is None:
            raise ValueError("Order type is required")
        if self.order_type not in OrderType:
            raise ValueError(f"Invalid order type: {self.order_type}")

        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("Limit price must be greater than 0")

        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("Stop price must be greater than 0")

        if (
            self.time_in_force is not None
            and self.time_in_force not in TimeInForce
        ):
            raise ValueError(
                f"Invalid time in force: {self.time_in_force}"
            )

        if self.limit_price is not None and self.stop_price is not None:
            raise ValueError(
                "Limit price and stop price cannot be set at the same time"
            )

        if (
            self.limit_price is not None
            and self.order_type != OrderType.LIMIT
        ):
            raise ValueError(
                "Limit price can only be set for limit orders"
            )

        if (
            self.stop_price is not None
            and self.order_type != OrderType.STOP
        ):
            raise ValueError(
                "Stop price can only be set for stop orders"
            )


class OrderStatus(StrEnum):
    """
    Define the lifecycle states of an order.

    Members
    -------
    REJECTED
        The platform or broker rejected the order.
    ACCEPTED
        The broker accepted the order.
    PENDING
        The order was submitted but has not yet reached a final state.
    FILLED
        The complete requested quantity was filled.
    CANCELLED
        The order was cancelled before receiving any additional fills.
    EXPIRED
        The order expired according to its time-in-force policy.
    PARTIALLY_FILLED
        Part of the requested quantity was filled and the remainder is still
        active.
    PARTIALLY_CANCELLED
        Part of the requested quantity was filled before the remainder was
        cancelled.
    PARTIALLY_EXPIRED
        Part of the requested quantity was filled before the remainder
        expired.
    """

    REJECTED = "rejected"
    ACCEPTED = "accepted"
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PARTIALLY_FILLED = "partially_filled"
    PARTIALLY_CANCELLED = "partially_cancelled"
    PARTIALLY_EXPIRED = "partially_expired"


class Order:
    """
    Represent a platform-managed snapshot of an order.

    The runtime creates and updates order instances from platform or broker
    events. Strategy code should inspect these values but should not modify
    them to simulate order state changes.

    Attributes
    ----------
    order_intent
        Original parameters used to submit the order.
    order_id
        Broker or platform order identifier, or ``None`` before one is
        assigned.
    status
        Current lifecycle state of the order.
    filled_quantity
        Total quantity filled so far, or ``None`` when no fill information is
        available.
    average_fill_price
        Volume-weighted average fill price, or ``None`` when no fills have
        occurred.
    message
        Human-readable status, cancellation, or rejection information.
    submitted_at
        Timestamp when the order was submitted, or ``None`` when unavailable.
    updated_at
        Timestamp of the latest order update, or ``None`` when unavailable.
    """

    def __init__(
        self,
        order_intent: OrderIntent,
        order_id: OrderId | None = None,
        status: OrderStatus = OrderStatus.PENDING,
        filled_quantity: QuantityValue | None = None,
        average_fill_price: PriceValue | None = None,
        message: str | None = None,
        submitted_at: Timestamp | None = None,
        updated_at: Timestamp | None = None,
    ) -> None:
        """
        Initialize an order snapshot.

        Parameters
        ----------
        order_intent
            Original parameters used to submit the order.
        order_id
            Broker or platform identifier assigned to the order.
        status
            Initial lifecycle status of the order.
        filled_quantity
            Quantity already filled.
        average_fill_price
            Volume-weighted average price of completed fills.
        message
            Optional human-readable status or rejection message.
        submitted_at
            Timestamp when the order was submitted.
        updated_at
            Timestamp of the most recent order update.
        """
        self.order_intent = order_intent
        self.order_id = order_id
        self.status = status
        self.filled_quantity = filled_quantity
        self.average_fill_price = average_fill_price
        self.message = message
        self.submitted_at = submitted_at
        self.updated_at = updated_at

    @property
    def is_active(self) -> bool:
        """
        Indicate whether the order can still receive fills or updates.

        Returns
        -------
        bool
            ``True`` when the order is pending, accepted, or partially
            filled; otherwise ``False``.
        """
        return self.status in {
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
        }

    @property
    def is_done(self) -> bool:
        """
        Indicate whether the order has reached a terminal state.

        Returns
        -------
        bool
            ``True`` when the order is rejected, filled, cancelled, expired,
            partially cancelled, or partially expired; otherwise ``False``.
        """
        return self.status in {
            OrderStatus.REJECTED,
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
            OrderStatus.PARTIALLY_CANCELLED,
            OrderStatus.PARTIALLY_EXPIRED,
        }

    @property
    def remaining_quantity(self) -> QuantityValue:
        """
        Return the quantity that has not yet been filled.

        Returns
        -------
        QuantityValue
            Requested quantity minus the reported filled quantity. When no
            fill quantity is available, returns the full requested quantity.
        """
        if self.filled_quantity is None:
            return self.order_intent.quantity

        return self.order_intent.quantity - self.filled_quantity

    @property
    def fill_ratio(self) -> float | None:
        """
        Return the filled portion of the requested quantity.

        Returns
        -------
        float | None
            Value calculated as ``filled_quantity / requested_quantity``, or
            ``None`` when the requested quantity is zero or no filled quantity
            has been reported.
        """
        if self.order_intent.quantity == 0:
            return None

        if self.filled_quantity is None:
            return None

        return safe_div(
            self.filled_quantity,
            self.order_intent.quantity,
        )

    @property
    def has_fills(self) -> bool:
        """
        Indicate whether the order status reports at least one fill.

        Returns
        -------
        bool
            ``True`` when the order is filled, partially filled, partially
            cancelled, or partially expired; otherwise ``False``.
        """
        return self.status in {
            OrderStatus.FILLED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.PARTIALLY_CANCELLED,
            OrderStatus.PARTIALLY_EXPIRED,
        }