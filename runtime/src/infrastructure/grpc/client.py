from __future__ import annotations

import grpc

from alphovex_sdk import OrderIntent, OrderId

from application.ports.order_submit_port import OrderSubmitPort
from application.context.logging_context import RuntimeLoggingContext
from infrastructure.config.config import RuntimeConfig 

class GRPCOrderSubmitClient(OrderSubmitPort):
    def __init__(
        self,
        config: RuntimeConfig,
        logger: RuntimeLoggingContext
    ) -> None:
        self._risk_ip = config.risk_grpc_IP
        self._logger = logger

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
        self._logger.platform_info(
            message="Order submit requested",
            order_intent= order_intent,
            id= client_order_id
        )
        self._logger.info(
            message="Order submit requested",
            order_intent= order_intent,
            id= client_order_id
        )

    def cancel_order(
        self,
        order_id: OrderId,
    ) -> None:
        self._logger.platform_info(
            message="Order cancel requested",
            id= order_id
        )
        self._logger.info(
            message="Order cancel requested",
            id= order_id
        )

    def cancel_all_orders(self) -> None:
        self._logger.platform_info(
            message="All pending Order cancel requested"
        )
        self._logger.info(
            message="All pending Order cancel requested"
        )

        