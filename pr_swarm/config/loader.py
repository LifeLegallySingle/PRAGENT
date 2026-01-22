"""Configuration loader for the PR Agent Swarm.

This loader reads a YAML configuration file and resolves any environment
variable placeholders. Placeholders follow the syntax ``${VAR:default}``,
where ``VAR`` is the environment variable name and ``default`` is an
optional fallback if the variable is not set. Nested data structures are
handled recursively.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml


_ENV_PATTERN = re.compile(r"\${([^:}]+)(?::([^}]*))?}")


def _resolve_value(value: Any) -> Any:
    """Recursively resolve environment variables in strings."""
    if isinstance(value, dict):
        return {k: _resolve_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item) for item in value]
    if isinstance(value, str):
        def replacer(match: re.Match[str]) -> str:
            var, default = match.group(1), match.group(2) or ""
            return os.getenv(var, default)
        return _ENV_PATTERN.sub(replacer, value)
    return value


def load_config(path: str) -> Dict[str, Any]:
    """Load and resolve a YAML configuration file.

    Parameters
    ----------
    path: str
        Path to the YAML configuration file.

    Returns
    -------
    Dict[str, Any]
        The parsed and resolved configuration dictionary.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with config_path.open("r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}
    return _resolve_value(raw_config)