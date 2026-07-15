from __future__ import annotations

from collections import deque

import uuid
import json
from datetime import datetime


from alphovex_sdk.context.order_context import OrderContext
from alphovex_sdk.models.order import (
    Order,
    OrderIntent,
    OrderSide,
    OrderStatus
)

from alphovex_sdk.models.order import TimeInForce

from .position_context import RuntimePositionContext
from application.ports.order_submit_port import OrderSubmitPort
from infrastructure.storage.client import StorageClient
from infrastructure.config.config import RuntimeConfig


class RuntimeOrderContext(OrderContext):
    """
    How to store orders
    - Active Orders are stored in RAM
    - MAX number of order history are stored in RAM
    """
    def __init__(
        self, 
        order_submit_client: OrderSubmitPort, 
        storage_client: StorageClient,
        config: RuntimeConfig,
        position_context: RuntimePositionContext
    ):
        self._orders = deque[Order](maxlen=config.MAX_ORDER_HISTORY)
        self._active_orders = deque[Order]
        self._order_submit_client = order_submit_client
        self._storage_client = storage_client
        self._today_orders_count : int = 0
        self._position_context = position_context
    
    def buy(
        self, 
        symbol, 
        quantity, 
        order_type, 
        limit_price = None, 
        stop_price = None, 
        time_in_force = TimeInForce.DAY
    ):
        buy_order_intent = OrderIntent(
            symbol=symbol, 
            side = OrderSide.BUY, 
            quantity=quantity, 
            order_type=order_type, 
            limit_price=limit_price, 
            stop_price=stop_price, 
            time_in_force=time_in_force
        )
        
        client_order_id = str(uuid.uuid4())

        new_order = Order(
                order_intent=buy_order_intent,
                order_id= client_order_id,
                submitted_at=datetime.now()
            )
        self._orders.append(new_order)
        self._active_orders.append(new_order)
        self._today_orders_count += 1
        self._order_submit_client.send_order_intent(buy_order_intent, client_order_id)
    
    def sell(
        self, 
        symbol, 
        quantity, 
        order_type, 
        limit_price = None, 
        stop_price = None, 
        time_in_force = TimeInForce.DAY
    ):
        sell_order_intent = OrderIntent(
            symbol=symbol, 
            side = OrderSide.SELL, 
            quantity=quantity, 
            order_type=order_type, 
            limit_price=limit_price, 
            stop_price=stop_price, 
            time_in_force=time_in_force
        )
        
        client_order_id = str(uuid.uuid4())

        new_order = Order(
                order_intent=sell_order_intent,
                order_id= client_order_id,
                submitted_at=datetime.now()
            )
        self._orders.append(new_order)
        self._active_orders.append(new_order)
        self._today_orders_count += 1
        self._order_submit_client.send_order_intent(sell_order_intent, client_order_id)
    
    def cancel_with_id(self, order_id: str):
        self._order_submit_client.cancel_order(order_id= order_id)

    def cancel_all(self):
        self._order_submit_client.cancel_all_orders()
    
    def cancel_with_symbol(self, symbol: str):
        for order in self._active_orders:
            if order.order_intent.symbol ==  symbol:
                self._order_submit_client.cancel_order(order_id=order.order_ref)

    def get_all_active_orders(self) -> tuple[Order, ...]:
        return tuple(self._active_orders)

    def get_active_order_with_id(self, order_id) -> Order | None:
        return next(
            (o for o in self._active_orders if o.order_ref == order_id),
            None
        )

    def get_active_orders_with_symbol(self, symbol: str) -> tuple[Order, ...]:
        return tuple([
            o for o in self._active_orders if o.order_intent.symbol == symbol
        ])
    
    def get_recent_orders(self, count: int = 1) -> tuple[Order, ...]:
        return tuple(self._orders[-count:])
    
    def get_today_order_count(self) -> int:
        return self._today_orders_count

    def reset_today_orders_count(self):
        self._today_orders_count = 0
    
    def update_order_status(
            self, 
            status: OrderStatus, 
            order_id: str,
            filled_quantity: float | None = None,
            average_fill_price: float | None = None        
        ):
        
        target_order = self.get_active_order_with_id(order_id=order_id)
        
        if target_order is not None:
            ## TODO - Update position info
            # self._position_context.update_positions()
            
            target_order.status = status
            target_order.update_at = datetime.now()
            if filled_quantity is not None:
                target_order.filled_quantity = filled_quantity
            if average_fill_price is not None:
                target_order.average_fill_price = average_fill_price

        if not target_order.is_active():
            self.save_order_in_storage(target_order)
            self._active_orders.remove(target_order)

    def save_order_in_storage(self, order: Order):
        record = self._order_to_dict(order)
        self._storage_client.store_order(record)

    def _order_to_dict(self, order: Order) -> dict:
        return {
            "order_id": order.order_id,
            "status": order.status.name if order.status else None,
            "filled_quantity": order.filled_quantity if order.filled_quantity else None,
            "average_fill_price": order.average_fill_price if order.average_fill_price else None,
            "message": order.message if order.message else None,
            "submitted_at": str(order.submitted_at) if order.submitted_at else None,
            "updated_at": str(order.updated_at) if order.updated_at else None,
            "intent": self._order_intent_to_dict(order.order_intent),
        }


    def _order_intent_to_dict(self, intent: OrderIntent) -> dict:
        return {
            "symbol": str(intent.symbol),
            "side": intent.side.name,
            "quantity": float(intent.quantity),
            "price": float(intent.price),
            "order_type": intent.order_type.name,
            "limit_price": float(intent.limit_price) if intent.limit_price else None,
            "stop_price": float(intent.stop_price) if intent.stop_price else None,
            "time_in_force": intent.time_in_force.name if intent.time_in_force else None,
        }
