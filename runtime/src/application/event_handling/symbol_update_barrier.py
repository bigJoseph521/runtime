from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from application.event_handling.tick_dispatcher import TickDispatcher


@dataclass(slots=True)
class _SymbolState:
    latest_direct_sequence: int | None = None
    pending_sequence: int | None = None
    pending_tick: Any = None
    applied_sequences: dict[str, int] = field(default_factory=dict)

    def reset(self) -> None:
        self.latest_direct_sequence = None
        self.pending_sequence = None
        self.pending_tick = None
        self.applied_sequences.clear()


class SymbolUpdateBarrier:
    """Release only fully synchronized, latest-only symbol tick callbacks."""

    def __init__(
        self,
        dispatcher: TickDispatcher,
        required_timeframes: Callable[[str], frozenset[str]],
    ) -> None:
        self._dispatcher = dispatcher
        self._required_timeframes = required_timeframes
        self._states: dict[str, _SymbolState] = {}

    def timeframe_applied(
        self,
        symbol: str,
        timeframe: str,
        source_sequence: int,
        tick: Any = None,
    ) -> None:
        normalized_symbol = str(symbol).strip().upper()
        normalized_timeframe = str(timeframe).strip().lower()
        state = self._states.setdefault(normalized_symbol, _SymbolState())

        if normalized_timeframe == "1m" and tick is not None:
            if (
                source_sequence == 0
                or (
                    state.latest_direct_sequence is not None
                    and source_sequence < state.latest_direct_sequence
                )
            ):
                state.reset()

            state.latest_direct_sequence = source_sequence
            state.pending_sequence = source_sequence
            state.pending_tick = tick

        state.applied_sequences[normalized_timeframe] = source_sequence
        self._release_if_ready(normalized_symbol, state)

    def _release_if_ready(
        self,
        symbol: str,
        state: _SymbolState,
    ) -> None:
        sequence = state.pending_sequence
        if sequence is None:
            return

        required = set(self._required_timeframes(symbol))
        required.add("1m")
        if any(
            state.applied_sequences.get(timeframe) != sequence
            for timeframe in required
        ):
            return

        # Consume the synchronized tick even when the strategy calculation is
        # busy. This deliberately coalesces callbacks instead of queueing them.
        tick = state.pending_tick
        state.pending_sequence = None
        state.pending_tick = None
        self._dispatcher.dispatch(symbol, tick)
