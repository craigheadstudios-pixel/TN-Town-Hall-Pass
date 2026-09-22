from datetime import datetime, timedelta

import pytest
import responses
from dateutil import tz

from scraper.config import Source
from scraper.platforms.base import ScrapeError
from scraper.platforms.civicengage import CivicEngageScraper

TZ = tz.gettz("America/Chicago")


def url_date(dt: datetime) -> str:
    return dt.strftime("%m%d%Y")


def make_source(**options):
    return Source(
        id="example-council",
        county="Example",
        jurisdiction="City of Example",
        body="City Council",
        category="city_council",
        platform="civicengage",
        calendar_url="https://example.gov/AgendaCenter",
        options=options,
    )


def build_page(upcoming, older_within_lookback, category_name_council="City Council"):
    return f"""
    <html><body>
    <h2>{category_name_council}</h2>
    <ul>
      <li><a href="/AgendaCenter/ViewFile/Agenda/_{url_date(upcoming)}-100">
        {upcoming.strftime('%B %d, %Y')} - 6:00 PM - City Council Regular Meeting</a></li>
      <li><a href="/AgendaCenter/ViewFile/Minutes/_{url_date(older_within_lookback)}-99">Minutes</a></li>
      <li><a href="/AgendaCenter/ViewFile/Agenda/_{url_date(older_within_lookback)}-99">
        {older_within_lookback.strftime('%B %d, %Y')} Agenda</a></li>
    </ul>
    <h2>Planning Commission</h2>
    <ul>
      <li><a href="/AgendaCenter/ViewFile/Agenda/_{url_date(upcoming)}-50">
        {upcoming.strftime('%B %d, %Y')} - 5:30 PM Agenda</a></li>
    </ul>
    </body></html>
    """


@responses.activate
def test_fetch_parses_agenda_links_with_category_filter():
    now = datetime.now(TZ)
    upcoming = now + timedelta(days=5)
    recent = now - timedelta(hours=2)

    responses.add(
        responses.GET,
        "https://example.gov/AgendaCenter",
        body=build_page(upcoming, recent),
        status=200,
    )
    source = make_source(category_name="City Council")
    meetings = CivicEngageScraper(source).fetch()

    # Only the two City Council agenda links, not Minutes, not Planning Commission.
    assert len(meetings) == 2
    starts = sorted(m.start for m in meetings)
    assert starts[0].date() == recent.date()
    assert starts[1].date() == upcoming.date()

    upcoming_meeting = next(m for m in meetings if m.start.date() == upcoming.date())
    assert upcoming_meeting.start.hour == 18
    assert upcoming_meeting.start.minute == 0
    assert "AgendaCenter" in upcoming_meeting.agenda_url


@responses.activate
def test_fetch_without_category_filter_returns_all_categories():
    now = datetime.now(TZ)
    upcoming = now + timedelta(days=5)
    recent = now - timedelta(hours=2)

    responses.add(
        responses.GET,
        "https://example.gov/AgendaCenter",
        body=build_page(upcoming, recent),
        status=200,
    )
    source = make_source()  # no category_name -> keep everything
    meetings = CivicEngageScraper(source).fetch()

    assert len(meetings) == 3  # 2 City Council + 1 Planning Commission


@responses.activate
def test_fetch_respects_lookback_cutoff():
    now = datetime.now(TZ)
    upcoming = now + timedelta(days=5)
    too_old = now - timedelta(days=40)

    responses.add(
        responses.GET,
        "https://example.gov/AgendaCenter",
        body=build_page(upcoming, too_old),
        status=200,
    )
    source = make_source(category_name="City Council")
    meetings = CivicEngageScraper(source).fetch()

    # The too-old agenda should be dropped by the default 1-day lookback.
    assert len(meetings) == 1
    assert meetings[0].start.date() == upcoming.date()


@responses.activate
def test_fetch_uses_default_time_when_none_in_text():
    now = datetime.now(TZ)
    upcoming = now + timedelta(days=5)
    html = f"""
    <html><body>
    <h2>City Council</h2>
    <a href="/AgendaCenter/ViewFile/Agenda/_{url_date(upcoming)}-1">Agenda, no time listed</a>
    </body></html>
    """
    responses.add(responses.GET, "https://example.gov/AgendaCenter", body=html, status=200)
    source = make_source(category_name="City Council", default_time="19:30")
    meetings = CivicEngageScraper(source).fetch()
    assert len(meetings) == 1
    assert meetings[0].start.hour == 19
    assert meetings[0].start.minute == 30


@responses.activate
def test_no_matching_links_raises_scrape_error():
    responses.add(
        responses.GET,
        "https://example.gov/AgendaCenter",
        body="<html><body><p>Nothing to see here.</p></body></html>",
        status=200,
    )
    with pytest.raises(ScrapeError, match="no AgendaCenter agenda links"):
        CivicEngageScraper(make_source()).fetch()


@responses.activate
def test_category_filter_with_no_matches_raises_scrape_error():
    now = datetime.now(TZ)
    upcoming = now + timedelta(days=5)
    recent = now - timedelta(hours=2)
    responses.add(
        responses.GET,
        "https://example.gov/AgendaCenter",
        body=build_page(upcoming, recent),
        status=200,
    )
    source = make_source(category_name="School Board")  # not present on this page
    with pytest.raises(ScrapeError, match="School Board"):
        CivicEngageScraper(source).fetch()


def test_missing_calendar_url_raises():
    source = make_source()
    source.calendar_url = ""
    with pytest.raises(ScrapeError, match="calendar_url"):
        CivicEngageScraper(source).fetch()


@responses.activate
def test_http_error_raises_scrape_error():
    responses.add(responses.GET, "https://example.gov/AgendaCenter", status=500)
    with pytest.raises(ScrapeError):
        CivicEngageScraper(make_source()).fetch()
