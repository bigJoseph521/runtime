from __future__ import annotations

from typing import Any
from abc import abstractmethod
from dataclasses import dataclass, field

@dataclass
class StorageContext:
    """
    Public SDK interface for strategy-owned storage.

    Strategy developers can store and retrieve their own custom values.
    The data is persisted in a JSON file on the server.
    Developers interact with storage using `set()` and `get()`

    Important rules
    ---------------
    
    - Values must be JSON-compatible (str, int, float, bool, None, list, dict)
    - Storage is per strategy instance
    - Do not use StorageContext to store platform-owned data:
        - orders, fills, positions, balances
        - risk limits
        - broker account status
        - portfolio ledger records

    Example
    -------
    ```python
    # Save a counter
    self.storage.set("counter", 20)

    # Save a list of symbols
    self.storage.set(
        "selected_symbols",
        ["AAPL","MSFT"]
    )

    # Save a small state dict
    self.storage.set(
        "rebalance_state",
        {"last_date": "2026-06-01", "enabled": True}
    )

    # Retrive a value with default
    count = self.storage.get("counter")
    symbols = self.storage.get("selected_symbols")
    ```     
    """

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Save a value in strategy storage.

        Parameters
        ----------
        key: str
            Name of the value to save.

            The key must be a non-empty string, e.g. "selected_symbols"
        
        value: Any
            value to save

            The value must be JSON-saveable. e.g. "registered", 12, {"a": 12, "b": 13}, [12, 13]
        
        Returns
        -------
        None
            The value is saved under the give key.
        
        Raises
        ------
        InvalidValueError
            Raised if the key is empty
            Raised if the value cannot be saved as JSON
        
        OutOfRangeError
            Raised if saving the value would exceed the allowed strategy storage quota.

        InvalidFormatError
            Raised if the runtime fails to serialize the value into the platform-managed
            JSON storage file.
        
        InvalidStateError
            Raised if strategy storage is unavailable

            Raised if strategy is not allowed to write to storage
        """
        ...

    @abstractmethod
    def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Read a value from strategy storage

        Parameters
        ----------
        key: str
            Name of the value to read

            The key must be a non-empty string, e.g. "selected_symbols"
        
        default: Any, default = None
            Value to return when the key does not exist

            In most strategy code, it's better to omit default and handle
            missing values explicitly
        
        Returns
        -------
        Saved value | None | default value

        Raises
        ------
        InvalidValueError
            Raised if the key is empty
        
        InvalidFormatError
            Raised if the runtime fails to read or decode the value from
            platform-managed JSON storage file.
        
        InvalidStateError
            Raised if strategy storage is unavailable
        """
        ...
