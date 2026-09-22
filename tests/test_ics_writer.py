from datetime import datetime, timezone
from pathlib import Path

from icalendar import Calendar

from scraper.ics_writer import build_calendar, write_all_feeds
from scraper.models import Meeting


def make_meeting(**overrides):
    defaults = dict(
        source_id="rutherford-county-commission",
        jurisdiction="Rutherford County",
        body="County Commission",
        county="Rutherford",
        category="county_commission",
        title="Regular Meeting",
        start=datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc),
        agenda_url="https://example.gov/agenda.pdf",
        location="Courthouse",
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def test_build_calendar_produces_parseable_ics():
    meetings = [make_meeting()]
    cal = build_calendar(meetings, name="Test Calendar")
    raw = cal.to_ical()
    reparsed = Calendar.from_ical(raw)
    events = list(reparsed.walk("VEVENT"))
    assert len(events) == 1
    assert "Rutherford County" in str(events[0]["summary"])
    assert str(events[0]["location"]) == "Courthouse"


def test_build_calendar_sorts_by_start():
    early = make_meeting(start=datetime(2026, 1, 1, tzinfo=timezone.utc), title="Early")
    late = make_meeting(start=datetime(2026, 6, 1, tzinfo=timezone.utc), title="Late")
    cal = build_calendar([late, early], name="Test")
    events = list(cal.walk("VEVENT"))
    starts = [e["dtstart"].dt for e in events]
    assert starts == sorted(starts)


def test_write_all_feeds_creates_combined_county_and_jurisdiction_files(tmp_path: Path):
    meetings = [
        make_meeting(),
        make_meeting(
            source_id="murfreesboro-city-council",
            jurisdiction="City of Murfreesboro",
            body="City Council",
            category="city_council",
        ),
        make_meeting(
            source_id="sumner-county-commission",
            jurisdiction="Sumner County",
            county="Sumner",
        ),
    ]
    written = write_all_feeds(meetings, tmp_path)

    assert (tmp_path / "all-meetings.ics").exists()
    assert (tmp_path / "counties" / "rutherford.ics").exists()
    assert (tmp_path / "counties" / "sumner.ics").exists()
    assert (tmp_path / "jurisdictions" / "rutherford-county-commission.ics").exists()
    assert (tmp_path / "jurisdictions" / "murfreesboro-city-council.ics").exists()
    assert len(written) == 1 + 2 + 3

    combined = Calendar.from_ical((tmp_path / "all-meetings.ics").read_bytes())
    assert len(list(combined.walk("VEVENT"))) == 3

    rutherford_county = Calendar.from_ical((tmp_path / "counties" / "rutherford.ics").read_bytes())
    assert len(list(rutherford_county.walk("VEVENT"))) == 2
