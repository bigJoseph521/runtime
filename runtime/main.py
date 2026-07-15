from __future__ import annotations

import sys
import signal
import asyncio

from alphovex_sdk import StrategyContext

from src.domain.model import RuntimeMode

from src.application.context.account_context import RuntimeAccountContext
from src.application.context.data_context import RuntimeDataContext
from src.application.context.indicator_context import RuntimeIndicatorContext
from src.application.context.logging_context import RuntimeLoggingContext
from src.application.context.order_context import RuntimeOrderContext
from src.application.context.params_context import RuntimeParamsContext
from src.application.context.position_context import RuntimePositionContext
from src.application.context.storage_context import RuntimeStorageContext
from src.application.context.time_context import RuntimeTimeContext

from src.application.status_managing.manager import StatusManager
from src.application.status_managing.status_model import Status
from src.application.event_handling.internal_event_bus import InternalEventBus
from src.application.event_handling.external_event_bus import ExternalEventBus
from src.application.event_handling.events_model import InternalEventType, ExternalEventType
from src.application.warm_up.warmup_service import WarmUpService
from src.application.symbol_reference.symbol_reference import SymbolReferenceService

from src.infrastructure.config.arg_parser import arg_parse
from src.infrastructure.config.config import RuntimeConfig
from src.infrastructure.http.sds_client import SDSHTTPClient
from src.infrastructure.grpc.historical_data_client import (
    GRPCHistoricalDataClient,
)
from src.infrastructure.storage.client import StorageClient
from src.infrastructure.strategy_loader.local_loader import LocalStrategyLoader
from src.infrastructure.nats.nats_client import NATSMarketDataClient
from src.infrastructure.grpc.client import GRPCClient

async def main():
    args = arg_parse()
    config = RuntimeConfig()
    config.env_load()
    storage_client = StorageClient(
        storage_path=config.storage_path, 
        market_data_path=config.market_data_path
    )
    logger = RuntimeLoggingContext(storage_client=storage_client)
    if args.mode == None:        
        internal_event_bus = InternalEventBus()
        sds_client = SDSHTTPClient(
            sds_base_url=config.SDS_base_url,
            deployment_id=config.deployment_id,
            http_timeout=config.http_timeout,
            logger=logger,
            event_bus=internal_event_bus
        )
        status_manager = StatusManager(logger=logger, report_client=sds_client)    
        internal_event_bus.subscribe(
            event_type = InternalEventType.STATUS_CHANGED, 
            handler = status_manager.transform
        )
        deployment_info = await sds_client.get_deployment_info()
        
        if deployment_info is not None:
            config.runtime_mode = deployment_info.mode
            config.strategy_uri = deployment_info.artifact_uri
            config.strategy_entrypoint = deployment_info.entrypoint
            config.strategy_zipfile_sha256 = deployment_info.artifact_digest

            symbol_reference_service = SymbolReferenceService(
                database_path= config.market_data_path + "/symbol_reference.db",
                data_provider= "Massive",
                broker=deployment_info.account.broker,
                logger= logger
            )

            strategy_loader = LocalStrategyLoader(
                logger=logger, 
                config=config,
                status_manager=status_manager
            )
            strategy_class = strategy_loader.load_strategy()
            
            params_context= RuntimeParamsContext(
                yaml_path=f"{config.strategy_local_path}/params.yaml",
                logger=logger,
                status_manager=status_manager
            )
            params_context.set_params(deployment_info.params)            
            await status_manager.transform(new_status=Status.STARTING)
            hds_client = GRPCHistoricalDataClient(
                target=config.HDS_grpc_target,
                timeout_seconds=config.grpc_timeout_seconds,
                logger=logger,
            )

            data_context = RuntimeDataContext(
                storage_client= storage_client,
                logger= logger,
                event_bus= internal_event_bus,
                symbol_reference_service=symbol_reference_service,
                status_manager=status_manager,
                hds_client=hds_client
            )

            account_context = RuntimeAccountContext(
                account = deployment_info.account
            )

            position_context = RuntimePositionContext(deployment_info.positions)

            grpc_client=GRPCClient(config=config)
            order_context = RuntimeOrderContext(
                order_submit_client=grpc_client,
                storage_client=storage_client,
                config=config,
                position_context=position_context,
            )

            indicator_context = RuntimeIndicatorContext(
                internal_event_bus=internal_event_bus,
                status_manager=status_manager,
                logger=logger,
                symbol_reference_service=symbol_reference_service
            )

            storage_context = RuntimeStorageContext(
                storage_client=storage_client
            )

            time_context = RuntimeTimeContext(
                logger=logger,
                event_bus=internal_event_bus
            )

            strategy_context = StrategyContext(
                account_context=account_context,
                data_context=data_context,
                indicator_context=indicator_context,
                logging_context=logger,
                order_context=order_context,
                params_context=params_context,
                position_context=position_context,
                time_context=time_context,
                storage_context=storage_context
            )            

            external_event_bus = ExternalEventBus()
            external_event_bus.subscribe(
                event_type=ExternalEventType.TICK,
                handler=data_context.update_ticks
            )
            external_event_bus.subscribe(
                event_type=ExternalEventType.TICK,
                handler=time_context.update_time_from_market_data
            )

            external_event_bus.subscribe(
                event_type=ExternalEventType.QUOTE,
                handler=data_context.update_quote
            )
            external_event_bus.subscribe(
                event_type=ExternalEventType.QUOTE,
                handler=time_context.update_time_from_market_data
            )

            external_event_bus.subscribe(
                event_type=ExternalEventType.CURRENT_BAR,
                handler=data_context.update_bars
            )

            external_event_bus.subscribe(
                event_type=ExternalEventType.ORDER_UPDATE,
                handler=order_context.update_order_status
            )

            external_event_bus.subscribe(
                event_type=ExternalEventType.WARMUP_BAR,
                handler=data_context.update_bars
            )
            external_event_bus.subscribe(
                event_type=ExternalEventType.WARMUP_BAR,
                handler=indicator_context.update_indicator
            )

            market_data_listener = NATSMarketDataClient(
                event_bus=external_event_bus,
                config=config,
                logger=logger
            )
            await market_data_listener.start()

            warm_up_service = WarmUpService(
                hds_client= hds_client,
                logger= logger,
                external_event_bus= external_event_bus,
                internal_event_bus= internal_event_bus
            )

            internal_event_bus.subscribe(
                event_type=InternalEventType.INDICATOR_REGISTERED,
                handler= warm_up_service.warm_up
            )

            internal_event_bus.subscribe(
                event_type=InternalEventType.WARMUP_FINISHED,
                handler=market_data_listener.add_channel
            )        
            internal_event_bus.subscribe(
                event_type=InternalEventType.INDICATOR_UNREGISTERED,
                handler=market_data_listener.remove_channel
            )
            internal_event_bus.subscribe(
                event_type=InternalEventType.INDICATOR_ALL_UNREGISTERED,
                handler=market_data_listener.unsubscribe_all_channels
            )
            runtime_strategy = strategy_class()
            runtime_strategy._bind_context(strategy_context)
            runtime_strategy.initialize()

            shutdown_event = asyncio.Event()

            def request_shutdown() -> None:
                shutdown_event.set()

            loop = asyncio.get_running_loop()

            # add_signal_handler works on Linux, including Kubernetes containers.
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(
                        sig,
                        request_shutdown,
                    )
                except NotImplementedError:
                    # Fallback for Windows.
                    signal.signal(
                        sig,
                        lambda *_: loop.call_soon_threadsafe(
                            shutdown_event.set,
                        ),
                    )

            try:
                logger.platform_info(
                    message="Strategy worker runtime started",
                )

                await status_manager.transform(
                    new_status=Status.RUNNING,
                )

                # This keeps main() and the event loop alive.
                await shutdown_event.wait()

            finally:
                logger.platform_info(
                    message="Strategy worker runtime stopping",
                )
                
                await status_manager.transform(
                    new_status=Status.STOPPING,
                )

                await market_data_listener.stop()
                await hds_client.close()

                # Close these too if their classes provide async close methods.
                # await grpc_client.close()
                # await sds_client.close()
                
                await status_manager.transform(
                    new_status=Status.STOPPED,
                )

                logger.platform_info(
                    message="Strategy worker runtime stopped",
                )

if __name__ == "__main__":
    asyncio.run(main())
