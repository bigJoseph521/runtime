from __future__ import annotations

from collections import deque
from pathlib import Path

from alphovex_sdk.indicators.examples.BB import BB
from alphovex_sdk import Bar

from .utils import jsonl_path, make_jsonl_line, read_jsonl


PERIOD = 20
DEVIATION = 2.0
SHIFT = 0
PRICE_TYPE = "close"

output_path = (
    "/home/akao/Videos/v1.1/runtime_v2/"
    "test/indicators/sample/BB/test_results.jsonl"
)

file_path = Path(output_path)
file_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

bb = BB(
    period=PERIOD,
    deviation=DEVIATION,
    shift=SHIFT,
    price_type=PRICE_TYPE,
)

bars: deque[Bar] = deque(
    maxlen=bb.required_history,
)

previous_timestamp: int | str | None = None


with file_path.open(
    "w",
    encoding="utf-8",
) as file:
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
            # Add the new forming bar.
            # The previous bars[0] becomes the latest completed bar.
            bars.appendleft(current_bar)

        else:
            # Replace the current forming-bar update.
            bars[0] = current_bar

        previous_timestamp = timestamp

        result = bb.calculate(
            list(bars),
            is_new_bar,
        )

        if result is None:
            middle = None
            upper = None
            lower = None
        else:
            middle, upper, lower = result

        file.write(
            make_jsonl_line(
                timestamp=timestamp,
                is_new=is_new_bar,
                ready=len(bars) >= bb.required_history,
                middle=middle,
                upper=upper,
                lower=lower,
                period=PERIOD,
                deviation=DEVIATION,
                shift=SHIFT,
                price_type=PRICE_TYPE,
            )
        )