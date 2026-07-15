from __future__ import annotations

from typing import Any

import json
from datetime import datetime

def to_jsonl_text(log_level: str, message: str, **kwargs: Any) -> str:
        log_record = {
        "ts": str(datetime.now()),
        "level": log_level,
        "message": message,
        **kwargs
        }

        return json.dumps(log_record)
