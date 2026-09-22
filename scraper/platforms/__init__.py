from scraper.platforms.base import BaseScraper, ScrapeError
from scraper.platforms.legistar import LegistarScraper
from scraper.platforms.ical_feed import ICalScraper
from scraper.platforms.civicengage import CivicEngageScraper
from scraper.platforms.manual import ManualScraper, UnimplementedPlatformScraper

REGISTRY: dict[str, type[BaseScraper]] = {
    "legistar": LegistarScraper,
    "ical": ICalScraper,
    "manual": ManualScraper,
    "civicengage": CivicEngageScraper,
    "civicclerk": UnimplementedPlatformScraper,
    "boarddocs": UnimplementedPlatformScraper,
    "boeconnect": UnimplementedPlatformScraper,
    "granicus_html": UnimplementedPlatformScraper,
    "primegov": UnimplementedPlatformScraper,
}


def get_scraper_class(platform: str) -> type[BaseScraper]:
    try:
        return REGISTRY[platform]
    except KeyError:
        raise ScrapeError(f"no scraper registered for platform {platform!r}")


__all__ = [
    "BaseScraper",
    "ScrapeError",
    "LegistarScraper",
    "ICalScraper",
    "CivicEngageScraper",
    "ManualScraper",
    "UnimplementedPlatformScraper",
    "REGISTRY",
    "get_scraper_class",
]
