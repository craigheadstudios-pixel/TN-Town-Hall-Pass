"""Generates .ics calendar files from lists of Meeting objects."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from icalendar import Calendar, Event

from scraper.models import Meeting, slugify

CALENDAR_NAME_PREFIX = "TN Town Hall Pass"


def build_calendar(meetings: list[Meeting], name: str, description: str = "") -> Calendar:
    cal = Calendar()
    cal.add("prodid", "-//TN Town Hall Pass//tn-town-hall-pass//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", name)
    if description:
        cal.add("x-wr-caldesc", description)
    cal.add("x-published-ttl", "PT12H")

    for meeting in sorted(meetings, key=lambda m: m.start):
        event = Event()
        event.add("uid", meeting.uid)
        event.add("summary", f"{meeting.jurisdiction} — {meeting.body}")
        event.add("dtstart", meeting.start)
        if meeting.end:
            event.add("dtend", meeting.end)
        else:
            event.add("duration", timedelta(hours=1))
        if meeting.location:
            event.add("location", meeting.location)

        description_lines = []
        if meeting.title and meeting.title != meeting.body:
            description_lines.append(meeting.title)
        if meeting.notes:
            description_lines.append(meeting.notes)
        if meeting.agenda_url:
            description_lines.append(f"Agenda: {meeting.agenda_url}")
        if meeting.source_url:
            description_lines.append(f"Source: {meeting.source_url}")
        if description_lines:
            event.add("description", "\n".join(description_lines))

        if meeting.agenda_url:
            event.add("url", meeting.agenda_url)
        elif meeting.source_url:
            event.add("url", meeting.source_url)

        cal.add_component(event)

    return cal


def write_calendar(meetings: list[Meeting], out_path: Path, name: str, description: str = "") -> None:
    cal = build_calendar(meetings, name=name, description=description)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(cal.to_ical())


def write_all_feeds(meetings: list[Meeting], out_dir: Path) -> list[Path]:
    """Writes per-jurisdiction, per-county, and one combined .ics feed.

    Returns the list of file paths written.
    """
    written: list[Path] = []

    # Combined statewide (well, pilot-wide) feed.
    combined_path = out_dir / "all-meetings.ics"
    write_calendar(
        meetings,
        combined_path,
        name=f"{CALENDAR_NAME_PREFIX} — All Meetings",
        description="Every public meeting tracked by TN Town Hall Pass.",
    )
    written.append(combined_path)

    # Per-county feeds.
    counties: dict[str, list[Meeting]] = {}
    for m in meetings:
        counties.setdefault(m.county, []).append(m)
    for county, county_meetings in counties.items():
        path = out_dir / "counties" / f"{slugify(county)}.ics"
        write_calendar(
            county_meetings,
            path,
            name=f"{CALENDAR_NAME_PREFIX} — {county} County",
            description=f"Public meetings in {county} County, TN.",
        )
        written.append(path)

    # Per-jurisdiction feeds (one per sources.yaml entry).
    by_source: dict[str, list[Meeting]] = {}
    for m in meetings:
        by_source.setdefault(m.source_id, []).append(m)
    for source_id, source_meetings in by_source.items():
        jurisdiction = source_meetings[0].jurisdiction
        body = source_meetings[0].body
        path = out_dir / "jurisdictions" / f"{slugify(source_id)}.ics"
        write_calendar(
            source_meetings,
            path,
            name=f"{jurisdiction} {body}",
            description=f"Meetings for {jurisdiction} {body}, via TN Town Hall Pass.",
        )
        written.append(path)

    return written
