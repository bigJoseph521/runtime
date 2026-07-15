import json
from pathlib import Path
from typing import Any, Iterator


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """
    Read a JSONL file one line at a time.

    Blank lines are ignored. Each parsed JSON object is yielded immediately,
    so the entire file is not loaded into memory.
    """
    file_path = Path(path)

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error.msg}"
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number}, "
                    f"but received {type(record).__name__}"
                )

            yield record

def make_jsonl_line(**kwargs: Any) -> str:
    """
    Convert named arguments into one JSONL line.

    Returns
    -------
    str
        A serialized JSON object ending with a newline.
    """
    return json.dumps(
        kwargs,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"

jsonl_path = "/home/akao/Videos/v1.1/runtime_v2/test/indicators/sample/mock_1m_current_bars_5000_v2 (1).jsonl"