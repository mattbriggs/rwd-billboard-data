"""Logging configuration for the study system."""

from __future__ import annotations

import logging


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging.

    :param verbose: When ``True``, emit debug logs.
    """

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
