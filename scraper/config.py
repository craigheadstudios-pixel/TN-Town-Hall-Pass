"""Load and validate sources.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from scraper.models import VALID_CATEGORIES

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES_PATH = REPO_ROOT / "sources.yaml"

VALID_PLATFORMS = {
    "legistar",
    "ical",
    "civicengage",
    "civicclerk",
    "boarddocs",
    "boeconnect",
    "granicus_html",
    "primegov",
    "manual",
}


@dataclass
class Source:
    id: str
    county: str
    jurisdiction: str
    body: str
    category: str
    platform: str
    calendar_url: str
    timezone: str = "America/Chicago"
    options: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict) -> "Source":
        missing = [k for k in ("id", "county", "jurisdiction", "body", "category", "platform") if k not in raw]
        if missing:
            raise ValueError(f"source entry missing required field(s) {missing}: {raw}")

        if raw["category"] not in VALID_CATEGORIES:
            raise ValueError(
                f"source {raw['id']!r} has invalid category {raw['category']!r}, "
                f"must be one of {sorted(VALID_CATEGORIES)}"
            )
        if raw["platform"] not in VALID_PLATFORMS:
            raise ValueError(
                f"source {raw['id']!r} has invalid platform {raw['platform']!r}, "
                f"must be one of {sorted(VALID_PLATFORMS)}"
            )

        known_fields = {"id", "county", "jurisdiction", "body", "category", "platform", "calendar_url", "timezone"}
        options = {k: v for k, v in raw.items() if k not in known_fields}

        return cls(
            id=raw["id"],
            county=raw["county"],
            jurisdiction=raw["jurisdiction"],
            body=raw["body"],
            category=raw["category"],
            platform=raw["platform"],
            calendar_url=raw.get("calendar_url", ""),
            timezone=raw.get("timezone", "America/Chicago"),
            options=options,
        )


def load_sources(path: Optional[Path] = None, only: Optional[list[str]] = None) -> list[Source]:
    """Load sources.yaml into a list of Source objects.

    `only`, if given, filters to sources whose id is in the list (useful for
    testing a single jurisdiction while adding it).
    """
    path = path or DEFAULT_SOURCES_PATH
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []

    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a YAML list of source entries")

    sources = [Source.from_dict(entry) for entry in raw]

    ids = [s.id for s in sources]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate source ids in {path}: {sorted(dupes)}")

    if only:
        only_set = set(only)
        sources = [s for s in sources if s.id in only_set]
        found = {s.id for s in sources}
        missing = only_set - found
        if missing:
            raise ValueError(f"--only referenced unknown source id(s): {sorted(missing)}")

    return sources
