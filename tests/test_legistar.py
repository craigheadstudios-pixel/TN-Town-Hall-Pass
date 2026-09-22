import json

import pytest
import responses

from scraper.config import Source
from scraper.platforms.base import ScrapeError
from scraper.platforms.legistar import LegistarScraper

SAMPLE_EVENTS = [
    {
        "EventId": 1,
        "EventBodyName": "City Commission",
        "EventDate": "2026-03-10T00:00:00",
        "EventTime": "6:00 PM",
        "EventLocation": "City Hall, 123 Main St",
        "EventAgendaFile": "https://example.legistar.com/agenda1.pdf",
        "EventInSiteURL": "https://example.legistar.com/MeetingDetail.aspx?ID=1",
        "EventComment": None,
    },
    {
        "EventId": 2,
        "EventBodyName": "Planning Commission",
        "EventDate": "2026-03-12T00:00:00",
        "EventTime": "5:30 PM",
        "EventLocation": "City Hall, 123 Main St",
        "EventAgendaFile": None,
        "EventInSiteURL": "https://example.legistar.com/MeetingDetail.aspx?ID=2",
        "EventComment": None,
    },
]


def make_source(**options):
    return Source(
        id="mt-juliet-city-commission",
        county="Wilson",
        jurisdiction="City of Mt. Juliet",
        body="City Commission",
        category="city_council",
        platform="legistar",
        calendar_url="https://mtjuliet-tn.legistar.com/",
        options=options,
    )


@responses.activate
def test_fetch_parses_events():
    responses.add(
        responses.GET,
        "https://webapi.legistar.com/v1/mtjuliettn/events",
        body=json.dumps(SAMPLE_EVENTS),
        status=200,
        content_type="application/json",
    )
    source = make_source(legistar_client="mtjuliettn")
    meetings = LegistarScraper(source).fetch()

    assert len(meetings) == 2
    assert meetings[0].title == "City Commission"
    assert meetings[0].start.year == 2026
    assert meetings[0].start.hour == 18
    assert meetings[0].location == "City Hall, 123 Main St"
    assert meetings[0].agenda_url == "https://example.legistar.com/agenda1.pdf"


@responses.activate
def test_fetch_filters_by_body_name():
    responses.add(
        responses.GET,
        "https://webapi.legistar.com/v1/mtjuliettn/events",
        body=json.dumps(SAMPLE_EVENTS),
        status=200,
        content_type="application/json",
    )
    source = make_source(legistar_client="mtjuliettn", body_name="Planning Commission")
    meetings = LegistarScraper(source).fetch()

    assert len(meetings) == 1
    assert meetings[0].title == "Planning Commission"


def test_missing_client_raises():
    source = make_source()
    with pytest.raises(ScrapeError, match="legistar_client"):
        LegistarScraper(source).fetch()


@responses.activate
def test_http_error_raises_scrape_error():
    responses.add(
        responses.GET,
        "https://webapi.legistar.com/v1/badclient/events",
        status=404,
    )
    source = make_source(legistar_client="badclient")
    with pytest.raises(ScrapeError):
        LegistarScraper(source).fetch()
