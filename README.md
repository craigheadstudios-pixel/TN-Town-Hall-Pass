# TN Town Hall Pass

Find every city council meeting, county commission meeting, school board meeting,
and other public hearing in Tennessee — and get it on your calendar.

## Why

Local government is where most decisions that touch daily life actually get made,
but there's no single place to find out when your city council, county commission,
or school board is meeting. Every Tennessee municipality and county publishes its
own calendar, usually through one of a handful of vendor platforms (Legistar,
Granicus, BoardDocs, PrimeGov, CivicClerk), each with its own site layout and no
shared feed. TN Town Hall Pass aggregates them into one place and into standard
calendar subscriptions (`.ics`) that work in Google Calendar, Apple Calendar, and
Outlook without installing anything.

## How it works

1. **`sources.yaml`** — a config file listing every jurisdiction we track: which
   county it's in, what kind of body it is (county commission, city council,
   school board, other), and what platform its calendar runs on.
2. **`scraper/`** — a Python pipeline that reads `sources.yaml`, fetches each
   jurisdiction's meetings using a platform-specific adapter (one parser per
   *platform*, not per city — most TN local governments sit on a handful of
   vendor platforms), and normalizes everything into a common `Meeting` model.
3. **`site/feeds/`** — generated `.ics` calendar files: one per jurisdiction,
   one per county, and one combined statewide feed. Subscribe once, get every
   future meeting automatically, including updates. It lives inside `site/`
   so GitHub Pages (which only deploys that directory) actually serves it.
4. **`site/`** — a static directory site (meant for GitHub Pages) that lists
   jurisdictions by county with "Subscribe" and "Add to Google Calendar" links,
   backed by the generated `site/data/meetings.json`.
5. **GitHub Actions** (`.github/workflows/update-feeds.yml`) re-runs the scraper
   on a schedule, commits the refreshed feeds/data, and redeploys the site — so
   feeds stay current without anyone running anything by hand.

## Coverage

Starting with a pilot of six Middle Tennessee counties to prove the pipeline
before expanding statewide:

- Robertson
- Sumner
- Wilson
- Rutherford
- Cheatham
- Putnam

Each county's coverage includes the county commission, the school board, and
city councils for the county seat and other incorporated cities within it. See
`sources.yaml` for the current jurisdiction list and `docs/COVERAGE.md` for
platform-by-platform notes on what's confirmed vs. still TODO.

## Supported platforms

A research pass over the six pilot counties (see `docs/COVERAGE.md`) found
that **CivicEngage (CivicPlus)** and **BoardDocs**, not Legistar, are the
dominant platforms among TN municipalities and school boards — Legistar shows
up in only one pilot jurisdiction so far. The platform table reflects that:

| Platform | Status | Notes |
|---|---|---|
| Legistar | Implemented | Uses the public Legistar Web API (JSON), no scraping needed |
| Direct iCal/RSS feed | Implemented | Any source that already publishes a `.ics` or meeting RSS feed (Granicus/iQM2, CivicClerk, CivicPlus "Notify Me", etc. — set `platform: ical` and point `calendar_url` at the feed itself) |
| CivicEngage (CivicPlus) | Implemented, unverified live | Most common platform among TN city/town councils. Parses the `/AgendaCenter` listing page by matching its date-embedded `ViewFile/Agenda/_MMDDYYYY-<id>` URL convention, with optional heading-based category filtering (`scraper/platforms/civicengage.py`). 10 pilot sources are wired up to it, but the exact AgendaCenter markup assumptions haven't been checked against a live page from this environment (see `docs/COVERAGE.md`) — first real signal comes from a GitHub Actions run |
| BoardDocs | Planned | Dominant platform for TN school boards; no public feed, requires HTML/JSON scraping |
| BOEconnect | Planned | Second common TN school-board platform; no public feed |
| CivicClerk | Planned | Emerging platform (a couple of pilot cities are mid-migration onto it); has a per-event ICS export worth targeting next |
| Granicus (HTML only, no feed) | Planned | Not found in the pilot six counties, but common elsewhere in TN |
| PrimeGov | Planned | Not found in the pilot six counties, but common elsewhere in TN |
| Manual/PDF-only | Fallback | Hand-curated `meetings:` list in `sources.yaml`; needed for jurisdictions with no vendor platform at all (roughly half the pilot's smaller towns and both county commissions) |

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the full pipeline: fetch all sources, write site/feeds/ and site/data/
python3 -m scraper.run

# Run just one source (useful while adding a new jurisdiction)
python3 -m scraper.run --only rutherford-county-commission
```

Generated output:
- `site/feeds/*.ics` — subscribable calendar feeds
- `site/data/meetings.json` — data backing the static site

## Adding a jurisdiction

1. Find the jurisdiction's public meeting calendar page.
2. Identify its platform (check the URL and page source for `legistar.com`,
   `granicus.com`/`iqm2.com`, `boarddocs.com`, `primegov.com`, `civicclerk.com`,
   or a CivicPlus "Notify Me" subscription link).
3. Add an entry to `sources.yaml` (see existing entries for the shape).
4. Run `python3 -m scraper.run --only <your-new-id>` and confirm meetings come
   back correctly.
5. Open a PR.

If the platform isn't supported yet, add the entry with `platform: manual` and
open an issue — untracked jurisdictions are exactly the gap this project exists
to close.

## Deployment

`.github/workflows/update-feeds.yml` runs the pipeline daily (and on demand
via "Run workflow"), commits any changed `feeds/`/`site/data/` files back to
`main`, and deploys `site/` to GitHub Pages. To enable it on a fork or new
repo: **Settings → Pages → Source: GitHub Actions**. It's also where sources
actually get scraped live for the first time — the sandbox this project was
originally built in has no outbound access to arbitrary external sites (see
`docs/COVERAGE.md`), but GitHub-hosted runners do.

`.github/workflows/test.yml` runs `pytest` on every push and PR.

## Project status

Early build. The pipeline, data model, and Legistar/iCal/CivicEngage
adapters work and are tested; `sources.yaml` lists all 33 jurisdictions in
the six-county pilot with real calendar/agenda page URLs. 10 of them (the
CivicEngage ones) run against a real adapter now, though it hasn't been
checked against a live page yet (this project's sandbox has no outbound
access to external sites — see `docs/COVERAGE.md`); the rest are still
`platform: manual` with no meetings. BoardDocs and BOEconnect (most school
boards in the pilot) are the next biggest gap. A native iPhone/Android app
is the long-term goal — the `.ics` feeds are the fastest way to get useful
today, since they work with zero install in every phone's built-in calendar
app.

## License

MIT — see `LICENSE`.
