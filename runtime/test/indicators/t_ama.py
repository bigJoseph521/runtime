from __future__ import annotations

from collections import deque
from pathlib import Path

from alphovex_sdk import Bar
from alphovex_sdk.indicators.examples.AMA import AMA

from .utils import jsonl_path, make_jsonl_line, read_jsonl


output_path = (
    "/home/akao/Videos/v1.1/runtime_v2/"
    "test/indicators/sample/AMA/test_results.jsonl"
)

file_path = Path(output_path)
file_path.parent.mkdir(parents=True, exist_ok=True)

ama_period = 10
fast_ma_period = 2
slow_ma_period = 30
shift = 0

indicator = AMA(
    ama_period=ama_period,
    fast_ma_period=fast_ma_period,
    slow_ma_period=slow_ma_period,
    shift=shift,
    price_type="open",
)

bars: deque[Bar] = deque(
    maxlen=indicator.required_history,
)

previous_timestamp: int | str | None = None

with file_path.open("w", encoding="utf-8") as file:
    for record in read_jsonl(jsonl_path):
        timestamp = record["timestamp"]

        current_bar = Bar(
            record["open"],
            record["high"],
            record["low"],
            record["close"],
            record["volume"],
            timestamp,
        )

        is_new_bar = (
            previous_timestamp is not None
            and timestamp != previous_timestamp
        )

        if previous_timestamp is None:
            bars.appendleft(current_bar)
        elif is_new_bar:
            bars.appendleft(current_bar)
        else:
            bars[0] = current_bar

        previous_timestamp = timestamp

        result = indicator.calculate(
            list(bars),
            is_new_bar,
        )

        # AMA returns a seed value when ama_period bars exist, but it is
        # fully ready only when one additional bar is available.
        ready = len(bars) >= indicator.required_history

        file.write(
            make_jsonl_line(
                timestamp=timestamp,
                is_new=is_new_bar,
                ready=ready,
                ama=(
                    float(result)
                    if result is not None
                    else None
                ),
                shift=shift,
            )
        )