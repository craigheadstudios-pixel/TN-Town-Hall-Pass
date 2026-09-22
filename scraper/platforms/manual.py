"""Fallbacks for sources that don't have an automated adapter (yet)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from dateutil import parser as dateutil_parser
from dateutil import tz

from scraper.platforms.base import BaseScraper, ScrapeError

if TYPE_CHECKING:
    from scraper.models import Meeting

logger = logging.getLogger(__name__)


class ManualScraper(BaseScraper):
    """Reads hand-curated meeting entries straight out of sources.yaml.

    Use this for jurisdictions on a platform we don't have a real adapter for
    yet, where someone has checked the meeting schedule by hand and recorded
    it under `meetings:` in the source's options. Each entry needs at least
    `title` and `start` (ISO 8601); `end`, `location`, `agenda_url` are
    optional. This is meant as a bridge, not a long-term solution — it goes
    stale the moment the real schedule changes.
    """

    def fetch(self) -> list["Meeting"]:
        from scraper.models import Meeting

        entries = self.source.options.get("meetings", [])
        if not entries:
            logger.warning(
                "source %s is platform=manual with no 'meetings:' entries in sources.yaml; "
                "returning no meetings",
                self.source.id,
            )
            return []

        default_tz = tz.gettz(self.source.timezone)
        meetings: list[Meeting] = []
        for entry in entries:
            try:
                start = _parse_dt(entry["start"], default_tz)
                end = _parse_dt(entry["end"], default_tz) if entry.get("end") else None
            except (KeyError, ValueError, OverflowError) as e:
                raise ScrapeError(f"source {self.source.id}: bad manual meeting entry {entry!r}: {e}") from e

            meetings.append(
                Meeting(
                    source_id=self.source.id,
                    jurisdiction=self.source.jurisdiction,
                    body=self.source.body,
                    county=self.source.county,
                    category=self.source.category,
                    title=entry.get("title", self.source.body),
                    start=start,
                    end=end,
                    location=entry.get("location"),
                    address=entry.get("address"),
                    agenda_url=entry.get("agenda_url"),
                    source_url=self.source.calendar_url,
                    notes=entry.get("notes"),
                )
            )
        return meetings


def _parse_dt(value: str, default_tz) -> datetime:
    dt = dateutil_parser.parse(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt


class UnimplementedPlatformScraper(BaseScraper):
    """Placeholder for platforms we know about but haven't built an adapter for.

    Fails loudly rather than silently returning no meetings, so a source
    misconfigured with a not-yet-supported platform is obvious in pipeline
    output instead of just quietly missing from feeds.
    """

    def fetch(self) -> list["Meeting"]:
        raise ScrapeError(
            f"source {self.source.id!r} uses platform={self.source.platform!r}, "
            "which doesn't have an adapter yet. Use platform: manual with a "
            "hand-curated 'meetings:' list in the meantime, or implement "
            f"scraper/platforms/{self.source.platform}.py."
        )
