import pytest

from scraper.config import Source
from scraper.platforms.base import ScrapeError
from scraper.platforms.manual import ManualScraper, UnimplementedPlatformScraper


def make_source(meetings=None):
    return Source(
        id="example-council",
        county="Example",
        jurisdiction="City of Example",
        body="City Council",
        category="city_council",
        platform="manual",
        calendar_url="https://example.gov/council",
        options={"meetings": meetings or []},
    )


def test_fetch_empty_meetings_returns_empty_list():
    assert ManualScraper(make_source()).fetch() == []


def test_fetch_parses_hand_entered_meetings():
    source = make_source(
        meetings=[
            {
                "title": "Regular Meeting",
                "start": "2026-04-01T18:00:00",
                "location": "City Hall",
            }
        ]
    )
    meetings = ManualScraper(source).fetch()
    assert len(meetings) == 1
    assert meetings[0].title == "Regular Meeting"
    assert meetings[0].location == "City Hall"
    assert meetings[0].start.tzinfo is not None


def test_fetch_bad_entry_raises_scrape_error():
    source = make_source(meetings=[{"title": "Missing start date"}])
    with pytest.raises(ScrapeError):
        ManualScraper(source).fetch()


def test_unimplemented_platform_raises():
    source = make_source()
    source.platform = "civicengage"
    with pytest.raises(ScrapeError, match="doesn't have an adapter"):
        UnimplementedPlatformScraper(source).fetch()
