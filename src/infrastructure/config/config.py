from __future__ import annotations

import os

from dataclasses import dataclass
from dotenv import load_dotenv

from domain.model import RuntimeMode

class RuntimeConfig:

    def __init__(self):
        self.deployment_id: str | None = None
        self.runtime_id : str | None = None

        self.market_data_path : str | None = None
        self.storage_path : str | None = None
        
        self.risk_grpc_IP : str | None = None
        
        self.SDS_base_url : str | None = None
        self.HDS_base_url : str | None = None
        self.NATS_server_url: str | None = None
        self.NATS_subject_prefix: str | None = None
        self.timeframe_service_base_url: str | None = None
        self.http_timeout: int | None = None
        
        self.md_redis_url: str | None = None
        self.md_redis_partition_count:  int | None = None
        
        self.MAX_ORDER_HISTORY : int | None = None
        self.tick_pubsub_channel_prefix: str | None = None
        self.quote_pubsub_channel_prefix: str | None = None

        self.runtime_mode: RuntimeMode = RuntimeMode.BACKTEST
        self.strategy_uri: str | None = None
        self.strategy_entrypoint: str | None = None
        self.strategy_local_path: str | None = None
        self.strategy_zipfile_sha256: str | None = None

    def env_load(self):
        load_dotenv()
        self.deployment_id = os.getenv("DEPLOYMENT_ID", "")
        self.runtime_id = os.getenv("RUNTIME_ID", "")

        self.market_data_path = os.getenv("MARKET_DATA_PATH", "data")
        self.storage_path = os.getenv("STORAGE_PATH", "data")
        
        self.risk_grpc_IP = os.getenv("SWR_RISK_GRPC_TARGET", "127.0.0.1:51051")
        
        self.SDS_base_url = os.getenv("STRATEGY_DEPLOYMENT_SERVICE_BASE_URL", "http://127.0.0.1:5010")
        self.HDS_base_url = os.getenv("HISTORICAL_DATA_SERVICE_BASE_URL", "http://127.0.0.1:5020")
        self.NATS_server_url = os.getenv(
            "NATS_SERVER_URL",
            os.getenv("NATS_SEVER_BASE_URL", "nats://127.0.0.1:4222"),
        )
        self.NATS_subject_prefix = os.getenv("NATS_SUBJECT_PREFIX", "md")
        self.timeframe_service_base_url = os.getenv(
            "TIMEFRAME_SERVICE_BASE_URL",
            "http://127.0.0.1:50120",
        )
        self.http_timeout = int(os.getenv("HTTP_TIMEOUT", "10"))
        
        self.md_redis_url = os.getenv("SWR_MARKET_DATA_REDIS_URL", "redis://127.0.0.1:6379/")
        self.md_redis_partition_count = os.getenv("MD_REDIS_PARTITION_COUNT", 128)
        self.tick_pubsub_channel_prefix = os.getenv("TICK_CHANNEL_PREFIX", "md:realtime:trades:")
        self.quote_pubsub_channel_prefix = os.getenv("QUOTE_CHANNEL_PREFIX", "md:realtime:quotes:")

        self.MAX_ORDER_HISTORY = os.getenv("MAX_ORDER_HISTORY", 100)

        self.strategy_local_path = os.getenv("STRATEGY_LOCAL_PATH", "./strategy")
