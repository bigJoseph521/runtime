from __future__ import annotations

from abc import ABC, abstractmethod

class StrategyLoaderPort(ABC):
    @abstractmethod
    def load_strategy(self, uri: str):
        ...