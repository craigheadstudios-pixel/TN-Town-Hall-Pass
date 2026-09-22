"""Shared interface every platform adapter implements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scraper.config import Source
    from scraper.models import Meeting


class ScrapeError(Exception):
    """Raised when a source can't be fetched or parsed."""


class BaseScraper:
    """Base class for platform adapters.

    Subclasses implement `fetch()`, which returns a list of `Meeting` objects
    for the given `Source`. Adapters should raise `ScrapeError` (not let
    arbitrary exceptions propagate) so the pipeline can report per-source
    failures without one bad source killing the whole run.
    """

    def __init__(self, source: "Source"):
        self.source = source

    def fetch(self) -> list["Meeting"]:
        raise NotImplementedError
