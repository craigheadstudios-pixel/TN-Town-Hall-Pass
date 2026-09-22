"""CLI entrypoint: load sources.yaml, fetch every source, write feeds/ and site/data/."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scraper.config import REPO_ROOT, load_sources
from scraper.ics_writer import write_all_feeds
from scraper.json_export import write_meetings_json
from scraper.platforms import ScrapeError, get_scraper_class

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("scraper.run")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="SOURCE_ID",
        help="only fetch these source ids from sources.yaml (for testing a single jurisdiction)",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=None,
        help="path to sources.yaml (default: repo root)",
    )
    parser.add_argument(
        "--out-feeds",
        type=Path,
        default=REPO_ROOT / "site" / "feeds",
        help=(
            "directory to write .ics feeds into (default: ./site/feeds -- inside the "
            "site directory so GitHub Pages, which only deploys site/, serves them)"
        ),
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=REPO_ROOT / "site" / "data" / "meetings.json",
        help="path to write the site's meetings.json (default: ./site/data/meetings.json)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="stop at the first source that fails to fetch, instead of skipping it",
    )
    args = parser.parse_args(argv)

    sources = load_sources(path=args.sources, only=args.only)
    if not sources:
        logger.error("no sources to fetch (check sources.yaml / --only)")
        return 1

    all_meetings = []
    failures: list[tuple[str, str]] = []

    for source in sources:
        scraper_cls = get_scraper_class(source.platform)
        logger.info("fetching %s (%s, platform=%s)", source.id, source.jurisdiction, source.platform)
        try:
            meetings = scraper_cls(source).fetch()
        except ScrapeError as e:
            logger.error("failed to fetch %s: %s", source.id, e)
            failures.append((source.id, str(e)))
            if args.fail_fast:
                return 1
            continue

        logger.info("  -> %d meeting(s)", len(meetings))
        all_meetings.extend(meetings)

    if not all_meetings:
        logger.warning("no meetings fetched from any source; writing empty feeds/data")

    written = write_all_feeds(all_meetings, args.out_feeds)
    logger.info("wrote %d .ics file(s) to %s", len(written), args.out_feeds)

    write_meetings_json(all_meetings, args.out_json)
    logger.info("wrote %s", args.out_json)

    if failures:
        logger.warning("%d source(s) failed:", len(failures))
        for source_id, message in failures:
            logger.warning("  - %s: %s", source_id, message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
