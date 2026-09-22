"""Adapter for jurisdictions hosted on Legistar (city/county council & committee
management software from Granicus). Many larger TN municipalities and some
counties use it. Rather than scraping the HTML calendar, this uses Legistar's
public Web API, which is JSON and doesn't require a key.

API docs: https://webapi.legistar.com/Help
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests

from scraper.models import Meeting
from scraper.platforms.base import BaseScraper, ScrapeError

logger = logging.getLogger(__name__)

USER_AGENT = (
    "TN-Town-Hall-Pass/0.1 (+https://github.com/craigheadstudios-pixel/tn-town-hall-pass; "
    "civic meeting aggregator; contact via GitHub issues)"
)


class LegistarScraper(BaseScraper):
    """Fetches meetings from a Legistar client's public events API.

    Requires `legistar_client` in the source's `sources.yaml` options: the
    client name used in that jurisdiction's Legistar subdomain, e.g. for
    https://rutherfordcountytn.legistar.com the client is `rutherfordcountytn`.

    Optional options:
      - `body_name`: restrict to one EventBodyName, for Legistar clients that
        host multiple boards/committees under a single client.
      - `lookahead_days`: currently unused server-side (Legistar returns all
        upcoming events), kept for future use if we need to page results.
    """

    API_BASE = "https://webapi.legistar.com/v1"

    def fetch(self) -> list[Meeting]:
        client = self.source.options.get("legistar_client")
        if not client:
            raise ScrapeError(f"source {self.source.id}: platform=legistar requires 'legistar_client' option")

        body_name = self.source.options.get("body_name")

        since = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        url = f"{self.API_BASE}/{client}/events"
        params = {
            "$filter": f"EventDate ge datetime'{since}'",
            "$orderby": "EventDate asc",
        }

        try:
            resp = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            raise ScrapeError(f"source {self.source.id}: Legistar API request failed: {e}") from e

        if not isinstance(data, list):
            raise ScrapeError(f"source {self.source.id}: unexpected Legistar API response shape: {type(data)}")

        meetings: list[Meeting] = []
        for event in data:
            if body_name and event.get("EventBodyName") != body_name:
                continue

            start = _parse_event_datetime(event, self.source.timezone)
            if start is None:
                logger.warning(
                    "source %s: skipping event %s with unparseable date/time",
                    self.source.id,
                    event.get("EventId"),
                )
                continue

            meetings.append(
                Meeting(
                    source_id=self.source.id,
                    jurisdiction=self.source.jurisdiction,
                    body=self.source.body,
                    county=self.source.county,
                    category=self.source.category,
                    title=event.get("EventBodyName") or self.source.body,
                    start=start,
                    location=event.get("EventLocation") or None,
                    agenda_url=event.get("EventAgendaFile") or event.get("EventInSiteURL") or None,
                    source_url=event.get("EventInSiteURL") or self.source.calendar_url,
                    notes=event.get("EventComment") or None,
                )
            )
        return meetings


def _parse_event_datetime(event: dict, timezone_name: str):
    from dateutil import tz

    date_raw = event.get("EventDate")
    if not date_raw:
        return None
    try:
        date_part = datetime.fromisoformat(date_raw.split("T")[0])
    except ValueError:
        return None

    time_raw = (event.get("EventTime") or "").strip()
    hour, minute = 0, 0
    if time_raw:
        try:
            parsed_time = datetime.strptime(time_raw.upper().replace(".", ""), "%I:%M %p")
            hour, minute = parsed_time.hour, parsed_time.minute
        except ValueError:
            logger.debug("could not parse EventTime %r, defaulting to midnight", time_raw)

    tzinfo = tz.gettz(timezone_name)
    return date_part.replace(hour=hour, minute=minute, tzinfo=tzinfo)
