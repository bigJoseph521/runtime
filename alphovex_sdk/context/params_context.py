from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ParamsContext(ABC):
    """
    Provide read-only access to strategy configuration parameters.

    Strategy parameters are supplied by the platform when a strategy is
    deployed or executed. Strategy code may read parameter values but should
    not modify the underlying configuration through this context.

    Parameter values may have different runtime types, such as strings,
    integers, floating-point values, booleans, lists, or dictionaries.
    """

    @abstractmethod
    def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Return a strategy parameter by key.

        Parameters
        ----------
        key
            Name of the parameter to retrieve.
        
        default
            Default value of the parameter

        Returns
        -------
        Any
            Stored parameter value.

        Raises
        ------
        KeyError
            Raised when the requested parameter does not exist.

        Examples
        --------
        ```python
        window_size = self.params.get("window_size", default=5)
        threshold = self.params.get("threshold")
        ```
        """
        ...

    @abstractmethod
    def get_params(
        self,
        *keys: str,
    ) -> tuple[Any, ...]:
        """
        Return multiple strategy parameters.

        Values are returned in the same order as the supplied keys.

        Parameters
        ----------
        *keys
            Names of the parameters to retrieve.

        Returns
        -------
        tuple[Any, ...]
            Parameter values ordered to match ``keys``.

        Raises
        ------
        KeyError
            Raised when any requested parameter does not exist.

        Examples
        --------
        ```python
        window_size, threshold = self.params.get_params(
            "window_size",
            "threshold",
        )
        ```
        """
        ...