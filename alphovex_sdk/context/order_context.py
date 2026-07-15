from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Order, OrderType, TimeInForce
from ..typedefs import (
    OrderId,
    PriceValue,
    QuantityValue,
    Symbol,
)


class OrderContext(ABC):
    """
    Provide order submission, cancellation, and query operations.

    Strategy code uses this context to submit buy and sell orders, cancel
    active orders, and inspect active or recently submitted orders.

    The platform owns order lifecycle state. Strategy code should not modify
    returned ``Order`` objects to simulate broker or exchange behavior.
    """

    @abstractmethod
    def buy(
        self,
        symbol: Symbol,
        quantity: QuantityValue,
        order_type: OrderType,
        *,
        limit_price: PriceValue | None = None,
        stop_price: PriceValue | None = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> None:
        """
        Submit a buy order.

        Parameters
        ----------
        symbol
            Symbol of the asset to buy.
        quantity
            Quantity to buy. Must be greater than zero.
        order_type
            Execution behavior requested for the order.
        limit_price
            Limit price for a limit order, or ``None`` when not applicable.
        stop_price
            Trigger price for a stop order, or ``None`` when not applicable.
        time_in_force
            Policy controlling how long the order remains active.

        Raises
        ------
        ValueError
            Raised when the quantity, price fields, or order configuration is
            invalid.
        """

        ...

    @abstractmethod
    def sell(
        self,
        symbol: Symbol,
        quantity: QuantityValue,
        order_type: OrderType,
        *,
        limit_price: PriceValue | None = None,
        stop_price: PriceValue | None = None,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> None:
        """
        Submit a sell order.

        Parameters
        ----------
        symbol
            Symbol of the asset to sell.
        quantity
            Quantity to sell. Must be greater than zero.
        order_type
            Execution behavior requested for the order.
        limit_price
            Limit price for a limit order, or ``None`` when not applicable.
        stop_price
            Trigger price for a stop order, or ``None`` when not applicable.
        time_in_force
            Policy controlling how long the order remains active.

        Raises
        ------
        ValueError
            Raised when the quantity, price fields, or order configuration is
            invalid.
        """

        ...

    @abstractmethod
    def cancel_all(self) -> int:
        """
        Request cancellation of all active orders.

        Returns
        -------
        int
            Number of active orders for which cancellation was requested.
        """

        ...

    @abstractmethod
    def cancel_with_symbol(
        self,
        symbol: Symbol,
    ) -> int:
        """
        Request cancellation of active orders for a symbol.

        Parameters
        ----------
        symbol
            Symbol whose active orders should be cancelled.

        Returns
        -------
        int
            Number of active orders for which cancellation was requested.
        """

        ...

    @abstractmethod
    def cancel_with_id(
        self,
        order_id: OrderId,
    ) -> bool:
        """
        Request cancellation of an active order.

        Parameters
        ----------
        order_id
            Platform or broker identifier of the order to cancel.

        Returns
        -------
        bool
            ``True`` when an active order was found and cancellation was
            requested; otherwise ``False``.
        """

        ...

    @abstractmethod
    def get_all_active_orders(self) -> tuple[Order, ...]:
        """
        Return all currently active orders.

        Returns
        -------
        tuple[Order, ...]
            Active orders known to the platform. Returns an empty tuple when no
            active orders exist.
        """

        ...

    @abstractmethod
    def get_active_order_with_id(
        self,
        order_id: OrderId,
    ) -> Order | None:
        """
        Return an active order by its identifier.

        Parameters
        ----------
        order_id
            Platform or broker order identifier.

        Returns
        -------
        Order | None
            Matching active order, or ``None`` when no active order has the
            specified identifier.
        """

        ...

    @abstractmethod
    def get_active_orders_with_symbol(
        self,
        symbol: Symbol,
    ) -> tuple[Order, ...]:
        """
        Return active orders for a symbol.

        Parameters
        ----------
        symbol
            Symbol whose active orders are requested.

        Returns
        -------
        tuple[Order]
            Matching active orders. Returns an empty tuple when no active
            orders exist for the symbol.
        """

        ...

    @abstractmethod
    def get_recent_orders(
        self,
        count: int = 1,
    ) -> tuple[Order, ...]:
        """
        Return recently submitted orders.

        Orders are returned from newest to oldest.

        Parameters
        ----------
        count
            Maximum number of recent orders to return.

        Returns
        -------
        tuple[Order, ...]
            Recent orders ordered from newest to oldest. Returns an empty tuple
            when no order history is available.

        Raises
        ------
        ValueError
            Raised when ``count`` is less than one.
        """

        ...

    @abstractmethod
    def get_today_order_count(self) -> int:
        """
        Return the number of orders submitted during the current trading day.

        Returns
        -------
        int
            Number of orders submitted during the current trading day.
        """

        ...