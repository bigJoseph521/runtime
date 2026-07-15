from __future__ import annotations

from abc import ABC, abstractmethod

from alphovex_sdk import OrderIntent, OrderId

class OrderSubmitPort(ABC):
    @abstractmethod
    def send_order_intent(self, order_intent: OrderIntent):
        ...
    
    @abstractmethod
    def cancel_order(self, order_id:OrderId):
        ...

    @abstractmethod
    def cancel_all_orders(self):
        ...
