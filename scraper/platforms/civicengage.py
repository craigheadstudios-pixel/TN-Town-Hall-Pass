"""Adapter for CivicPlus CivicEngage sites' AgendaCenter product.

AgendaCenter is CivicPlus's agenda/minutes archive, organized by "category"
(one category per board -- City Council, Planning Commission, Board of
Education, etc). Each posted agenda's file link embeds its meeting date in a
well-known, stable URL convention:

    /AgendaCenter/ViewFile/Agenda/_03102026-123
    /AgendaCenter/ViewFile/Minutes/03-10-2026-123

This adapter keys off that URL pattern rather than the page's CSS/DOM
structure, which varies across CivicPlus site themes/versions and can't be
verified live from an environment without outbound access to .gov/.org sites
(see docs/COVERAGE.md) -- the date-in-URL convention is the one part of
AgendaCenter's markup expected to be stable across sites. If a page's HTML
doesn't yield any matches, this raises ScrapeError rather than silently
returning zero meetings, since a real empty page and a wrong assumption
about markup would otherwise look identical.

Known limitation: AgendaCenter is an archive of *posted* agendas, not a true
forward calendar -- a meeting typically doesn't show up until its agenda is
published, often only days ahead. It's still the best structured, board-
specific source available without a confirmed feed URL.

Required options: none beyond the usual `calendar_url` (point it at the
site's /AgendaCenter root, or a category-specific sub-path if the site
supports one, e.g. https://lebanontn.org/AgendaCenter/City-Council-5).

Optional options:
  - `category_name`: the board name as it's expected to appear in an
    on-page heading (e.g. "City Council"). When set, only agenda links
    found under the nearest preceding heading whose text contains this
    string (case-insensitive) are kept -- needed when one AgendaCenter page
    lists multiple boards together. Leave unset when `calendar_url` is
    already scoped to one category, or to keep everything found.
  - `default_time`: "HH:MM" 24h, used when no meeting time can be found in
    the text near a link (default "18:00" -- most TN local meetings are
    evening).
  - `lookback_days`: how many days into the past to still include a posted
    agenda for (default 1 -- covers a meeting happening today whose agenda
    was posted this morning). Older agendas in the archive are skipped.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from scraper.models import Meeting
from scraper.platforms.base import BaseScraper, ScrapeError
from scraper.platforms.legistar import USER_AGENT

logger = logging.getLogger(__name__)

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

AGENDA_LINK_RE = re.compile(
    r"/AgendaCenter/ViewFile/(?P<doctype>Agenda|Minutes|Packet)/_?"
    r"(?P<month>\d{2})-?(?P<day>\d{2})-?(?P<year>\d{4})-(?P<item_id>\d+)",
    re.IGNORECASE,
)

TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*([AaPp][Mm])\b")


class CivicEngageScraper(BaseScraper):
    def fetch(self) -> list[Meeting]:
        if not self.source.calendar_url:
            raise ScrapeError(
                f"source {self.source.id}: platform=civicengage requires 'calendar_url' "
                "(the AgendaCenter page)"
            )

        try:
            resp = requests.get(self.source.calendar_url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ScrapeError(f"source {self.source.id}: failed to fetch AgendaCenter page: {e}") from e

        soup = BeautifulSoup(resp.text, "html.parser")
        category_name = self.source.options.get("category_name")
        default_time = self.source.options.get("default_time", "18:00")
        default_hour, default_minute = _parse_hhmm(default_time)
        lookback_days = self.source.options.get("lookback_days", 1)

        from dateutil import tz

        tzinfo = tz.gettz(self.source.timezone)
        cutoff = datetime.now(tzinfo) - timedelta(days=lookback_days)

        matches = _find_agenda_links(soup, category_name)
        if not matches:
            raise ScrapeError(
                f"source {self.source.id}: no AgendaCenter agenda links found at "
                f"{self.source.calendar_url}"
                + (f" matching category_name={category_name!r}" if category_name else "")
                + ". Either this jurisdiction doesn't actually run CivicPlus AgendaCenter "
                "(double-check platform_hint / calendar_url), or the site's markup doesn't "
                "match what this adapter expects -- inspect the live page and adjust "
                "scraper/platforms/civicengage.py accordingly."
            )

        by_item: dict[str, Meeting] = {}
        for link, link_text in matches:
            href = link.get("href", "")
            match = AGENDA_LINK_RE.search(href)
            if not match or match.group("doctype") not in ("Agenda", "Packet"):
                # Skip Minutes-only links so a meeting with both an Agenda
                # and Minutes link doesn't get counted twice; Agenda is
                # posted first and is the more useful "upcoming" signal.
                continue

            # Dedup on the AgendaCenter item id embedded in the URL, not the
            # date -- two different boards can post an agenda for the same
            # date, and deduping by date alone would silently drop one.
            item_key = match.group("item_id")
            if item_key in by_item:
                continue

            try:
                year, month, day = int(match.group("year")), int(match.group("month")), int(match.group("day"))
                time_match = TIME_RE.search(link_text)
                if time_match:
                    hour = int(time_match.group(1)) % 12
                    if time_match.group(3).lower() == "pm":
                        hour += 12
                    minute = int(time_match.group(2))
                else:
                    hour, minute = default_hour, default_minute

                start = datetime(year, month, day, hour, minute, tzinfo=tzinfo)
            except ValueError:
                logger.warning("source %s: skipping unparseable agenda link href=%r", self.source.id, href)
                continue

            if start < cutoff:
                continue

            by_item[item_key] = Meeting(
                source_id=self.source.id,
                jurisdiction=self.source.jurisdiction,
                body=self.source.body,
                county=self.source.county,
                category=self.source.category,
                title=link_text or self.source.body,
                start=start,
                agenda_url=urljoin(self.source.calendar_url, href),
                source_url=self.source.calendar_url,
            )

        return list(by_item.values())


def _find_agenda_links(soup: BeautifulSoup, category_name: str | None):
    """Walks the page in document order, tracking the most recent heading,
    and returns (link, link_text) pairs for AgendaCenter file links -- filtered
    to ones under a heading matching category_name, if given.

    This heuristic (heading precedes its section's content) doesn't depend on
    any particular CSS class or div structure, only on headings being used to
    label each category's group of agenda links, which is a common enough
    accessible-HTML pattern to be a reasonable bet without a live page to
    confirm against.
    """
    current_heading = None
    results = []
    for tag in soup.find_all(HEADING_TAGS.union({"a"})):
        if tag.name in HEADING_TAGS:
            current_heading = tag.get_text(" ", strip=True)
            continue
        href = tag.get("href", "")
        if not AGENDA_LINK_RE.search(href):
            continue
        if category_name and (current_heading is None or category_name.lower() not in current_heading.lower()):
            continue
        results.append((tag, tag.get_text(" ", strip=True)))
    return results


def _parse_hhmm(value: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = value.split(":")
        return int(hour_str), int(minute_str)
    except (ValueError, AttributeError):
        return 18, 0
