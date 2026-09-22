"""Adapter for sources that already publish a direct .ics calendar feed.

Covers Granicus/iQM2 sites and CivicPlus "Notify Me" subscriptions, among
others, whenever the jurisdiction exposes a subscribable iCal export. No HTML
scraping needed — just download and normalize. `calendar_url` must point at
the .ics feed URL itself, not the HTML calendar page.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time

import icalendar
import requests

from scraper.models import Meeting
from scraper.platforms.base import BaseScraper, ScrapeError
from scraper.platforms.legistar import USER_AGENT

logger = logging.getLogger(__name__)


class ICalScraper(BaseScraper):
    def fetch(self) -> list[Meeting]:
        if not self.source.calendar_url:
            raise ScrapeError(f"source {self.source.id}: platform=ical requires 'calendar_url'")

        try:
            resp = requests.get(self.source.calendar_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ScrapeError(f"source {self.source.id}: failed to fetch ical feed: {e}") from e

        try:
            cal = icalendar.Calendar.from_ical(resp.content)
        except ValueError as e:
            raise ScrapeError(f"source {self.source.id}: failed to parse ical feed: {e}") from e

        from dateutil import tz

        tzinfo = tz.gettz(self.source.timezone)

        meetings: list[Meeting] = []
        for component in cal.walk("VEVENT"):
            start = _to_aware_datetime(component.get("dtstart"), tzinfo)
            if start is None:
                continue
            end = _to_aware_datetime(component.get("dtend"), tzinfo)

            summary = str(component.get("summary")) if component.get("summary") else self.source.body
            location = str(component.get("location")) if component.get("location") else None
            description = str(component.get("description")) if component.get("description") else None
            url_prop = component.get("url")
            url = str(url_prop) if url_prop else None

            meetings.append(
                Meeting(
                    source_id=self.source.id,
                    jurisdiction=self.source.jurisdiction,
                    body=self.source.body,
                    county=self.source.county,
                    category=self.source.category,
                    title=summary,
                    start=start,
                    end=end,
                    location=location,
                    agenda_url=url,
                    source_url=self.source.calendar_url,
                    notes=description,
                )
            )
        return meetings


def _to_aware_datetime(prop, tzinfo):
    if prop is None:
        return None
    value = prop.dt
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=tzinfo)
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=tzinfo)
    return None
