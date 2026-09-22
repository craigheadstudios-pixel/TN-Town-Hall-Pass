import pytest
import responses

from scraper.config import Source
from scraper.platforms.base import ScrapeError
from scraper.platforms.ical_feed import ICalScraper

SAMPLE_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Example//EN
BEGIN:VEVENT
UID:1@example.gov
SUMMARY:Regular City Council Meeting
DTSTART:20260315T230000Z
DTEND:20260316T000000Z
LOCATION:City Hall
URL:https://example.gov/agenda.pdf
DESCRIPTION:Regular meeting of the city council.
END:VEVENT
BEGIN:VEVENT
UID:2@example.gov
SUMMARY:Budget Workshop
DTSTART;VALUE=DATE:20260320
END:VEVENT
END:VCALENDAR
"""


def make_source(calendar_url="https://example.gov/feed.ics"):
    return Source(
        id="example-council",
        county="Example",
        jurisdiction="City of Example",
        body="City Council",
        category="city_council",
        platform="ical",
        calendar_url=calendar_url,
    )


@responses.activate
def test_fetch_parses_vevents():
    responses.add(responses.GET, "https://example.gov/feed.ics", body=SAMPLE_ICS, status=200)
    meetings = ICalScraper(make_source()).fetch()

    assert len(meetings) == 2
    assert meetings[0].title == "Regular City Council Meeting"
    assert meetings[0].location == "City Hall"
    assert meetings[0].agenda_url == "https://example.gov/agenda.pdf"
    assert meetings[0].end is not None


@responses.activate
def test_fetch_handles_all_day_event_without_dtend():
    responses.add(responses.GET, "https://example.gov/feed.ics", body=SAMPLE_ICS, status=200)
    meetings = ICalScraper(make_source()).fetch()
    all_day = next(m for m in meetings if m.title == "Budget Workshop")
    assert all_day.start.hour == 0
    assert all_day.end is None


def test_missing_calendar_url_raises():
    source = make_source(calendar_url="")
    with pytest.raises(ScrapeError, match="calendar_url"):
        ICalScraper(source).fetch()


@responses.activate
def test_invalid_ics_raises_scrape_error():
    responses.add(responses.GET, "https://example.gov/feed.ics", body=b"not an ics file", status=200)
    with pytest.raises(ScrapeError):
        ICalScraper(make_source()).fetch()
