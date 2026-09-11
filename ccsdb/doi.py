"""DOI validation shared by paper search and entry creation."""

from __future__ import annotations

import re

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:a-z0-9]+$", re.IGNORECASE)


def normalize_doi(value: str | None) -> str:
    """Return a canonical DOI or an empty string when no DOI was supplied."""

    normalized = (value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :].strip()
            break
    return normalized.rstrip(".,; ")


def validate_doi(value: str | None) -> str:
    """Normalize and validate a DOI, raising ValueError for invalid input."""

    normalized = normalize_doi(value)
    if not normalized or not DOI_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid DOI, for example 10.1021/example.123")
    return normalized
