"""Utility for generating filesystem‑safe slugs from arbitrary text."""

from __future__ import annotations

import re

def slugify(value: str) -> str:
    """Convert the input string into a lowercase slug suitable for filenames.

    This function removes non‑alphanumeric characters, replaces them with
    hyphens, strips leading/trailing hyphens and collapses multiple
    consecutive hyphens into a single one.

    Examples
    --------
    >>> slugify("John D. O'Connor")
    'john-d-o-connor'
    >>> slugify("  A complex Name!  ")
    'a-complex-name'
    """
    value = value.strip().lower()
    # Replace all non‑alphanumeric characters with hyphens
    value = re.sub(r"[^a-z0-9]+", "-", value)
    # Remove leading and trailing hyphens
    value = value.strip("-")
    # Collapse multiple hyphens
    value = re.sub(r"-+", "-", value)
    return value