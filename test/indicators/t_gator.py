from __future__ import annotations

from collections import deque
from pathlib import Path

from alphovex_sdk import Bar
from alphovex_sdk.indicators.examples.Gator import Gator

from .utils import jsonl_path, make_jsonl_line, read_jsonl


output_path = (
    "/home/akao/Videos/v1.1/runtime_v2/"
    "test/indicators/sample/Gator/test_results.jsonl"
)

file_path = Path(output_path)
file_path.parent.mkdir(parents=True, exist_ok=True)

indicator = Gator(
    jaw_period=13,
    jaw_shift=8,
    teeth_period=8,
    teeth_shift=5,
    lips_period=5,
    lips_shift=3,
    price_type="median",
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

        upper, lower = indicator.calculate(
            list(bars),
            is_new_bar,
        )

        ready = (
            upper is not None
            and lower is not None
        )

        file.write(
            make_jsonl_line(
                ready=ready,
                upper=upper,
                lower=lower,
            )
        )