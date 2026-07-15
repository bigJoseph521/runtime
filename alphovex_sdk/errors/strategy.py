from __future__ import annotations

from enum import StrEnum

from .base import SDKError

class StrategyErrorCodeEnum(StrEnum):
    STRATEGY_CONTEXT_NOT_BOUND = "strategy_context_not_bound"
    STRATEGY_NOT_INITIALIZED = "strategy_not_initialized"

class StrategyContextNotFoundError(SDKError):
    """
    Raised when a strategy attempts to access ``StrategyContext`` before it is bound.

    This error indicates that the platform has not yet attached a valid
    ``StrategyContext`` to the strategy instance. Strategy code must not
    access context-dependent properties (such as ``self.data`` or
    ``self.orders``) before initialization is complete.

    Notes
    -----
    - This is a platform-level lifecycle error.
    - Users should not attempt to catch or handle this error in strategy code.
    - This typically indicates a runtime or integration issue.
    """

    def __init__(self) -> None:
        super().__init__(
            message="StrategyContext is not available. "
                    "The platform must bind the context before strategy usage.",
            code=StrategyErrorCodeEnum.STRATEGY_CONTEXT_NOT_BOUND,
            details={
                "reason": "context_not_bound",
                "hint": "Ensure initialize() is called after binding StrategyContext.",
            },
        )

class StrategyNotInitializedError(SDKError):
    """
    Raised when a strategy attempts to access context properties before it has been initialized.

    This error indicates that the strategy has not yet completed its initialization process, 
    which is required before context-dependent properties (such as ``self.data`` or ``self.order``) 
    can be accessed. The platform must call the ``initialize()`` method before these properties are available.

    Notes
    -----
    - This is a platform-level lifecycle error.
    - Users should not attempt to catch or handle this error in strategy code.
    - This typically indicates that the strategy's lifecycle was not properly managed or that 
      the platform failed to initialize the strategy context before usage.    
    """
    def __init__(self) -> None:
        super().__init__(
            message="Strategy is not initialized. "
            "The platform must call initialize() before accessing context properties.",
            code=StrategyErrorCodeEnum.STRATEGY_NOT_INITIALIZED,
            details={
                "reason": "strategy_not_initialized",
                "hint": "Ensure initialize() is called before accessing context properties.",
            },
        )