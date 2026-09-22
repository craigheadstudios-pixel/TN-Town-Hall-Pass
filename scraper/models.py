"""Common data model that every platform adapter normalizes into."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

VALID_CATEGORIES = {
    "county_commission",
    "city_council",
    "school_board",
    "other",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


@dataclass
class Meeting:
    """A single public meeting, normalized across all source platforms."""

    source_id: str          # id of the sources.yaml entry this came from
    jurisdiction: str        # e.g. "Rutherford County"
    body: str                # e.g. "County Commission"
    county: str              # e.g. "Rutherford"
    category: str            # one of VALID_CATEGORIES
    title: str                # meeting title, e.g. "Regular Commission Meeting"
    start: datetime            # timezone-aware
    end: Optional[datetime] = None
    location: Optional[str] = None
    address: Optional[str] = None
    agenda_url: Optional[str] = None
    source_url: str = ""
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"invalid category {self.category!r}, must be one of {sorted(VALID_CATEGORIES)}"
            )
        if self.start.tzinfo is None:
            raise ValueError(f"Meeting.start must be timezone-aware (got {self.start!r})")
        if self.end is not None and self.end.tzinfo is None:
            raise ValueError(f"Meeting.end must be timezone-aware (got {self.end!r})")

    @property
    def uid(self) -> str:
        """Stable identifier for de-duplication and ICS UID, independent of run order."""
        basis = f"{self.source_id}|{self.title}|{self.start.isoformat()}"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
        return f"{digest}@tn-town-hall-pass"

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "source_id": self.source_id,
            "jurisdiction": self.jurisdiction,
            "body": self.body,
            "county": self.county,
            "category": self.category,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat() if self.end else None,
            "location": self.location,
            "address": self.address,
            "agenda_url": self.agenda_url,
            "source_url": self.source_url,
            "notes": self.notes,
        }
