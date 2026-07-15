from __future__ import annotations

from pathlib import Path
from collections import deque

from alphovex_sdk import (    
    Bar
)

from alphovex_sdk.indicators.examples.MACD import MACD

from .utils import read_jsonl, jsonl_path, make_jsonl_line

output_path = "/home/akao/Videos/v1.1/runtime_v2/test/indicators/sample/MACD/test_results.jsonl"
file_path = Path(output_path)

myMACD = MACD()
bars : deque[Bar] = deque(maxlen=myMACD.required_history)


with file_path.open("w", encoding="utf-8") as file:
    for bar in read_jsonl(jsonl_path):
        # print(
        #     bar["timestamp"],
        #     bar["open"],
        #     bar["high"],
        #     bar["low"],
        #     bar["close"],
        #     bar["volume"],
        #     bar["is_new"],
        # )
        new_bar = Bar(
            bar["open"],
            bar["high"],
            bar["low"],
            bar["close"],
            bar["volume"],
            bar["timestamp"],
        )
        bars.appendleft(new_bar)
        result =  myMACD.calculate(list(bars), bar["is_new"])
        if result is not None:
            macd, signal, histogram = result
            file.write(make_jsonl_line(
                macd = macd,
                signal = signal,
                histogram = histogram
            ))
        else:
            file.write(make_jsonl_line(
                macd = None,
                signal = None,
                histogram = None
            ))


