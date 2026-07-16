from __future__ import annotations

import grpc

from alphovex_sdk import OrderIntent, OrderId

from application.ports.order_submit_port import OrderSubmitPort
from infrastructure.config.config import RuntimeConfig 

class GRPCOrderSubmitClient(OrderSubmitPort):
    def __init__(self, config: RuntimeConfig) -> None:
        self._risk_ip = config.risk_grpc_IP

    def send_order_intent(
        self,
        order_intent: OrderIntent,
        client_order_id: str,
    ) -> None:
        # Build and send the actual generated gRPC request here.
        #
        # request = SubmitOrderIntentRequest(
        #     client_order_id=client_order_id,
        #     symbol=order_intent.symbol,
        #     side=order_intent.side.value,
        #     quantity=float(order_intent.quantity),
        #     order_type=order_intent.order_type.value,
        #     limit_price=order_intent.limit_price,
        #     stop_price=order_intent.stop_price,
        #     time_in_force=order_intent.time_in_force.value,
        # )
        #
        # self._stub.SubmitOrderIntent(request)
        ...

    def cancel_order(
        self,
        order_id: OrderId,
    ) -> None:
        ...

    def cancel_all_orders(self) -> None:
        ...

        