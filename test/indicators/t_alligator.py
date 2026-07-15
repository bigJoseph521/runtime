from __future__ import annotations

from collections import deque
from pathlib import Path

from alphovex_sdk import Bar
from alphovex_sdk.indicators.examples.Alligator import Alligator

from .utils import jsonl_path, make_jsonl_line, read_jsonl


output_path = (
    "/home/akao/Videos/v1.1/runtime_v2/"
    "test/indicators/sample/Alligator/test_results.jsonl"
)

file_path = Path(output_path)
file_path.parent.mkdir(parents=True, exist_ok=True)

alligator = Alligator()

bars: deque[Bar] = deque(
    maxlen=alligator.required_history,
)

previous_timestamp: str | int | None = None


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
            # Add a new forming bar.
            # The previous bars[0] becomes bars[1].
            bars.appendleft(current_bar)

        else:
            # Replace the current forming bar instead of storing
            # multiple versions of the same candle.
            bars[0] = current_bar

        previous_timestamp = timestamp

        # Call calculate exactly once because the indicator keeps state.
        result = alligator.calculate(
            list(bars),
            is_new_bar,
        )

        if result is None:
            file.write(
                make_jsonl_line(
                    timestamp=timestamp,
                    is_new=is_new_bar,
                    ready=False,
                    jaw=None,
                    teeth=None,
                    lips=None,
                )
            )
            continue

        jaw, teeth, lips = result

        file.write(
            make_jsonl_line(
                timestamp=timestamp,
                is_new=is_new_bar,
                ready=True,
                jaw=jaw,
                teeth=teeth,
                lips=lips,
            )
        )