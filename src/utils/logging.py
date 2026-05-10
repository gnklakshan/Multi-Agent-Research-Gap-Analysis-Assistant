from __future__ import annotations

import logging
from typing import Optional

from rich.logging import RichHandler


def setup_logging(*, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

