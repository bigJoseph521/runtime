from __future__ import annotations

import numpy as np

bar_dtype = np.dtype([
    ("ts", "int64"),

    ("open", "float64"),
    ("high", "float64"),
    ("low", "float64"),
    ("close", "float64"),

    ("volume", "float64"),
])

tick_dtype = np.dtype([
    ("ts", "int64"),
    ("price", "float64"),
    ("volume", "float64"),
])

quote_dtype = np.dtype([
    ("ts", "int64"),
    ("bid", "float64"),
    ("ask", "float64"),

    ("bid_size", "float64"),
    ("ask_size", "float64"),
])