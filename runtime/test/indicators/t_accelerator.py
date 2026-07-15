from __future__ import annotations

from collections import deque
from pathlib import Path

from alphovex_sdk.indicators.examples.Accelerator import Accelerator
from alphovex_sdk import Bar

from .utils import jsonl_path, make_jsonl_line, read_jsonl


output_path = (
    "/home/akao/Videos/v1.1/runtime_v2/"
    "test/indicators/sample/Accelerator/test_results.jsonl"
)

file_path = Path(output_path)
file_path.parent.mkdir(parents=True, exist_ok=True)

accelerator = Accelerator()

bars: deque[Bar] = deque(
    maxlen=accelerator.required_history,
)

previous_timestamp: int | None = None


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
            # Insert the new forming bar.
            # The previous bars[0] becomes the latest completed bar.
            bars.appendleft(current_bar)

        else:
            # Replace the existing forming bar instead of appending
            # multiple updates of the same candle.
            bars[0] = current_bar

        previous_timestamp = timestamp

        result = accelerator.calculate(
            list(bars),
            is_new_bar,
        )

        file.write(
            make_jsonl_line(
                timestamp=timestamp,
                is_new=is_new_bar,
                ready=result is not None,
                accelerator=result,
            )
        )