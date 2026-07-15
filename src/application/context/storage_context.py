from __future__ import annotations

from alphovex_sdk.context.storage_context import StorageContext

from infrastructure.storage.client import StorageClient

class RuntimeStorageContext(StorageContext):
    def __init__(self, storage_client: StorageClient):
        self._storage_client = storage_client
    
    def get(self, key, default = None):
        return self._storage_client.get_user_record(key, default)
    
    def set(self, key, value):
        return self._storage_client.store_user_record(key, value)