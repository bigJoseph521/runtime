from __future__ import annotations

from abc import ABC, abstractmethod

from alphovex_sdk import OrderId, OrderIntent


class OrderSubmitPort(ABC):
    @abstractmethod
    def send_order_intent(
        self,
        order_intent: OrderIntent,
        client_order_id: str,
    ) -> None:
        """Submit an order intent with its runtime-generated idempotency ID."""
        ...

    @abstractmethod
    def cancel_order(
        self,
        order_id: OrderId,
    ) -> None:
        ...

    @abstractmethod
    def cancel_all_orders(self) -> None:
        ...