from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()

    with Path(path).open("rb") as file:
        while chunk := file.read(8192):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_check(file_path: str | Path, value: str) -> bool:
    return file_sha256(file_path) == value


# Example mypy output:
# sma_crossover.py:12:5: error: Incompatible types in assignment
MYPY_ERROR_REGEX = re.compile(
    r"^(?P<file>.*?):"
    r"(?P<row>\d+):"
    r"(?:(?P<column>\d+):)?"
    r"\s*error:\s*"
    r"(?P<message>.*?)"
    r"(?:\s+\[[^\]]+\])?$"
)


@dataclass(frozen=True, slots=True)
class TypeCheckError:
    type: str
    message: str
    file: str
    row: int
    column: int | None


def check_folder_with_mypy(
    folder_path: str | Path,
) -> list[dict[str, Any]]:
    folder = Path(folder_path).resolve()

    if not folder.is_dir():
        error = TypeCheckError(
            type="CHECK_ERROR",
            message=f"Folder does not exist: {folder}",
            file=str(folder),
            row=0,
            column=None,
        )
        return [asdict(error)]

    excluded_directories = {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "venv",
    }

    python_files = sorted(
        path.relative_to(folder)
        for path in folder.rglob("*.py")
        if not any(
            part in excluded_directories
            for part in path.relative_to(folder).parts
        )
    )

    if not python_files:
        return []

    # Expected structure:
    #
    # runtime_v2/
    # ├── alphovex_sdk/
    # └── strategy/
    #
    # folder is runtime_v2/strategy, so folder.parent is runtime_v2.
    project_root = folder.parent

    environment = os.environ.copy()
    existing_mypy_path = environment.get("MYPYPATH")

    if existing_mypy_path:
        environment["MYPYPATH"] = os.pathsep.join(
            [
                str(project_root),
                existing_mypy_path,
            ]
        )
    else:
        environment["MYPYPATH"] = str(project_root)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",

            # Ignore external mypy configuration files.
            "--config-file",
            os.devnull,

            # Check function bodies even without annotations.
            "--check-untyped-defs",

            # Support source folders without __init__.py files.
            "--explicit-package-bases",

            # Use the same Python environment as the runtime.
            "--python-executable",
            sys.executable,

            "--show-column-numbers",
            "--hide-error-context",
            "--hide-error-codes",
            "--no-error-summary",
            "--no-pretty",
            "--no-color-output",
            "--no-incremental",

            # Pass every strategy Python file explicitly.
            *(str(path) for path in python_files),
        ],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    output = "\n".join(
        stream.strip()
        for stream in (result.stdout, result.stderr)
        if stream.strip()
    )

    errors: list[TypeCheckError] = []

    for line in output.splitlines():
        match = MYPY_ERROR_REGEX.match(line.strip())

        if match is None:
            continue

        column_text = match.group("column")

        errors.append(
            TypeCheckError(
                type="TYPE_ERROR",
                message=match.group("message").strip(),
                file=match.group("file"),
                row=int(match.group("row")),
                column=int(column_text) if column_text else None,
            )
        )

    # Mypy normally returns:
    # 0 = no errors
    # 1 = type-checking errors
    # 2 or higher = mypy execution/configuration failure
    if result.returncode not in (0, 1):
        errors.append(
            TypeCheckError(
                type="CHECK_ERROR",
                message=output or "Mypy execution failed",
                file=str(folder),
                row=0,
                column=None,
            )
        )

    elif result.returncode == 1 and not errors:
        errors.append(
            TypeCheckError(
                type="CHECK_ERROR",
                message=output or "Mypy failed without parseable errors",
                file=str(folder),
                row=0,
                column=None,
            )
        )

    return [asdict(error) for error in errors]