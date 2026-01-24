"""Centralised logging configuration for the PR Agent Swarm.

This module sets up console and optional file logging. It configures a
consistent format across the project and allows the log level to be
controlled via an environment variable. File logging can be enabled via
configuration when constructing the logger.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional


def setup_logging(log_dir: Optional[str] = None) -> None:
    """Configure the root logger for the application.

    Parameters
    ----------
    log_dir: Optional[str]
        Directory where log files should be written. If ``None``, file
        logging is disabled and only console output is used.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.handlers = []  # Reset any existing handlers

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "pr_swarm.log"
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)