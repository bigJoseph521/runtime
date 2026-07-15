from __future__ import annotations

from typing import Any

import json

from alphovex_sdk.context.logging_context import LoggingContext

from infrastructure.storage.client import StorageClient

from application.utils import to_jsonl_text

class RuntimeLoggingContext(LoggingContext):
    def __init__(self, storage_client: StorageClient):
        self._client = storage_client    
    
    def debug(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("DEBUG", message, **kwargs)
        self._write_user_log(record=record)

    def info(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("INFO", message, **kwargs)
        self._write_user_log(record=record)

    def warning(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("WARNING", message, **kwargs)
        self._write_user_log(record=record)

    def error(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("ERROR", message, **kwargs)
        self._write_user_log(record=record)
    
    def platform_debug(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("DEBUG", message, **kwargs)
        self._write_platform_log(record=record)

    def platform_info(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("INFO", message, **kwargs)
        self._write_platform_log(record=record)

    def platform_warning(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("WARNING", message, **kwargs)
        self._write_platform_log(record=record)

    def platform_error(self, message: str, **kwargs: Any) -> None:
        record = to_jsonl_text("ERROR", message, **kwargs)
        self._write_platform_log(record=record)
    
    def _write_user_log(self, record: str):
        self._client.store_user_log(record=record)
    
    def _write_platform_log(self, record: str):
        self._client.store_platform_log(record=record)

