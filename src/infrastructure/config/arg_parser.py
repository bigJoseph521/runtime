from __future__ import annotations

import argparse

def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode")

    args = parser.parse_args()

    if args.mode is not None and args.mode.lower() != "backtest":
        raise ValueError(
            f"Invalid mode: {args.mode}. Allowed value is 'backtest'."
        )

    return args