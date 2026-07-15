from __future__ import annotations

import hashlib

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

print(
    file_sha256(
        "C:/Users/Administrator/Videos/v1.1/runtime/runtime/data/samples/sma_5m/sma_crossover.zip"
    )
)