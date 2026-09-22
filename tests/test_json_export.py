import json
from datetime import datetime, timezone
from pathlib import Path

from scraper.json_export import write_meetings_json
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
    )
    defaults.update(overrides)
    return Meeting(**defaults)


def test_write_meetings_json(tmp_path: Path):
    out_path = tmp_path / "meetings.json"
    write_meetings_json([make_meeting()], out_path)

    payload = json.loads(out_path.read_text())
    assert payload["meeting_count"] == 1
    assert payload["counties"] == ["Rutherford"]
    assert payload["jurisdictions"][0]["source_id"] == "rutherford-county-commission"
    assert payload["jurisdictions"][0]["feed"] == "feeds/jurisdictions/rutherford-county-commission.ics"
    assert payload["meetings"][0]["jurisdiction"] == "Rutherford County"
    assert "generated_at" in payload


def test_write_meetings_json_empty(tmp_path: Path):
    out_path = tmp_path / "meetings.json"
    write_meetings_json([], out_path)
    payload = json.loads(out_path.read_text())
    assert payload["meeting_count"] == 0
    assert payload["counties"] == []
    assert payload["meetings"] == []
