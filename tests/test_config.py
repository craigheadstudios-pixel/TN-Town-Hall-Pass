import textwrap
from pathlib import Path

import pytest

from scraper.config import load_sources


def write_sources(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text(textwrap.dedent(content))
    return path


def test_load_sources_basic(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: example-council
          county: Example
          jurisdiction: "City of Example"
          body: "City Council"
          category: city_council
          platform: manual
          calendar_url: "https://example.gov/council"
          meetings: []
        """,
    )
    sources = load_sources(path=path)
    assert len(sources) == 1
    assert sources[0].id == "example-council"
    assert sources[0].options["meetings"] == []


def test_duplicate_ids_rejected(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: dup
          county: Example
          jurisdiction: "A"
          body: "Council"
          category: city_council
          platform: manual
        - id: dup
          county: Example
          jurisdiction: "B"
          body: "Council"
          category: city_council
          platform: manual
        """,
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_sources(path=path)


def test_invalid_category_rejected(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: bad
          county: Example
          jurisdiction: "A"
          body: "Council"
          category: not_a_category
          platform: manual
        """,
    )
    with pytest.raises(ValueError, match="invalid category"):
        load_sources(path=path)


def test_invalid_platform_rejected(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: bad
          county: Example
          jurisdiction: "A"
          body: "Council"
          category: city_council
          platform: not_a_platform
        """,
    )
    with pytest.raises(ValueError, match="invalid platform"):
        load_sources(path=path)


def test_only_filter(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: a
          county: Example
          jurisdiction: "A"
          body: "Council"
          category: city_council
          platform: manual
        - id: b
          county: Example
          jurisdiction: "B"
          body: "Council"
          category: city_council
          platform: manual
        """,
    )
    sources = load_sources(path=path, only=["b"])
    assert [s.id for s in sources] == ["b"]


def test_only_filter_unknown_id_raises(tmp_path):
    path = write_sources(
        tmp_path,
        """
        - id: a
          county: Example
          jurisdiction: "A"
          body: "Council"
          category: city_council
          platform: manual
        """,
    )
    with pytest.raises(ValueError, match="unknown source id"):
        load_sources(path=path, only=["nonexistent"])
