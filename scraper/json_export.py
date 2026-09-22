"""Writes the JSON data file the static site reads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from scraper.models import Meeting, slugify


def write_meetings_json(meetings: list[Meeting], out_path: Path) -> None:
    sorted_meetings = sorted(meetings, key=lambda m: m.start)

    counties = sorted({m.county for m in meetings})
    jurisdictions = sorted(
        {(m.source_id, m.jurisdiction, m.body, m.county, m.category) for m in meetings},
        key=lambda t: (t[3], t[1], t[2]),
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meeting_count": len(sorted_meetings),
        "counties": counties,
        "jurisdictions": [
            {
                "source_id": source_id,
                "jurisdiction": jurisdiction,
                "body": body,
                "county": county,
                "category": category,
                "feed": f"feeds/jurisdictions/{slugify(source_id)}.ics",
            }
            for source_id, jurisdiction, body, county, category in jurisdictions
        ],
        "meetings": [m.to_dict() for m in sorted_meetings],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
