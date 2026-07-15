from __future__ import annotations

import grpc

from alphovex_sdk import OrderIntent, OrderId

from application.ports.order_submit_port import OrderSubmitPort
from infrastructure.config.config import RuntimeConfig 

class GRPCClient(OrderSubmitPort):
    def __init__(self, config: RuntimeConfig):
        self._risk_IP = config.risk_grpc_IP
    
    def send_order_intent(self, order_intent: OrderIntent):
        ...
    
    def cancel_order(self, order_id: OrderId):
        ...
    
    def cancel_all_orders(self):
        ...
    

        