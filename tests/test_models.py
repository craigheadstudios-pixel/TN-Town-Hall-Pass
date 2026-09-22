from datetime import datetime, timezone

import pytest

from scraper.models import Meeting, slugify


def make_meeting(**overrides):
    defaults = dict(
        source_id="rutherford-county-commission",
        jurisdiction="Rutherford County",
        body="County Commission",
        county="Rutherford",
        category="county_commission",
        title="Regular Meeting",
        start=datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def test_uid_is_stable_for_same_inputs():
    m1 = make_meeting()
    m2 = make_meeting()
    assert m1.uid == m2.uid


def test_uid_differs_when_start_differs():
    m1 = make_meeting()
    m2 = make_meeting(start=datetime(2026, 2, 15, 18, 0, tzinfo=timezone.utc))
    assert m1.uid != m2.uid


def test_naive_start_rejected():
    with pytest.raises(ValueError):
        make_meeting(start=datetime(2026, 1, 15, 18, 0))


def test_invalid_category_rejected():
    with pytest.raises(ValueError):
        make_meeting(category="not_a_real_category")


def test_to_dict_roundtrips_required_fields():
    m = make_meeting()
    d = m.to_dict()
    assert d["jurisdiction"] == "Rutherford County"
    assert d["category"] == "county_commission"
    assert d["start"] == m.start.isoformat()
    assert d["uid"] == m.uid


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Rutherford", "rutherford"),
        ("City of La Vergne", "city-of-la-vergne"),
        ("  Mt. Juliet  ", "mt-juliet"),
    ],
)
def test_slugify(value, expected):
    assert slugify(value) == expected
