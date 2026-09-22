# Coverage status

Tracks, per pilot jurisdiction, what platform it's on and whether an automated
adapter is wired up. Every entry in `sources.yaml` currently has
`platform: manual` with `meetings: []` — nothing is producing real meeting
data yet. `platform_hint` on each entry records what a research pass (web
search only, see caveat below) found; that's the starting point for building
and confirming a real adapter, not a confirmed working integration.

## Why everything is still "manual"

The sandbox this project was scaffolded in blocks outbound HTTPS to arbitrary
`.gov`/`.com`/`.org` domains at the network-policy level (only a short
allowlist — PyPI, npm, GitHub, Anthropic's own endpoints — is reachable). That
means no source in this list has been fetched live from here: `platform_hint`
values come from a web-search-only research pass and city/county/school-board
pages' own known platform fingerprints (URL patterns like `Calendar.aspx?EID=`
for CivicEngage, `go.boarddocs.com/tn/...` for BoardDocs, `*.legistar.com` for
Legistar), not from a confirmed page fetch.

**Next step for a human, or a Claude session with normal internet access (a
local machine, or GitHub Actions once `.github/workflows/update-feeds.yml`
runs on GitHub's infrastructure):** open each `calendar_url` below, confirm
the platform, find the real feed URL (or note there isn't one), and:
- if it's a direct `.ics`/RSS feed → set `platform: ical` with that URL, done
  (the adapter already exists and needs nothing else)
- if it's a Legistar site → confirm the `legistar_client` name and set
  `platform: legistar` (adapter already exists)
- if it's CivicEngage/BoardDocs/CivicClerk/BOEconnect → those adapters aren't
  built yet (see README's platform table); either build one, or hand-enter
  the schedule under `meetings:` with `platform: manual` in the meantime

## Pilot jurisdictions

| County | Jurisdiction | Body | `platform_hint` | Automated? |
|---|---|---|---|---|
| Robertson | Robertson County | County Commission | custom_pdf | no |
| Robertson | City of Springfield | Board of Mayor and Aldermen | civicengage | no |
| Robertson | City of Greenbrier | Board of Mayor and Aldermen | civicengage | no |
| Robertson | City of White House | Board of Mayor and Aldermen | civicengage | no |
| Robertson | Robertson County | Board of Education | custom_pdf | no |
| Sumner | Sumner County | County Commission | custom_pdf | no |
| Sumner | City of Gallatin | City Council | civicengage | no |
| Sumner | City of Hendersonville | Board of Mayor and Aldermen | civicengage | no |
| Sumner | City of Portland | City Council | civicclerk | no |
| Sumner | City of Westmoreland | City Council | custom_pdf | no |
| Sumner | City of Millersville | City Commission | custom_other | no |
| Sumner | Sumner County | Board of Education | boarddocs | no |
| Wilson | Wilson County | County Commission | civicengage | no |
| Wilson | City of Lebanon | City Council | civicengage | no |
| Wilson | City of Mt. Juliet | City Commission | **legistar** (best automation candidate — see `research_note` in sources.yaml) | no |
| Wilson | Town of Watertown | Board of Mayor and Aldermen | custom_pdf | no |
| Wilson | Wilson County | Board of Education | boarddocs | no |
| Rutherford | Rutherford County | County Commission | custom_pdf | no |
| Rutherford | City of Murfreesboro | City Council | civicengage | no |
| Rutherford | Town of Smyrna | Town Council | civicclerk | no |
| Rutherford | City of La Vergne | Board of Mayor and Aldermen | civicengage | no |
| Rutherford | City of Eagleville | City Council | custom_pdf | no |
| Rutherford | Rutherford County | Board of Education | custom_pdf | no |
| Rutherford | Murfreesboro City | Board of Education (separate district) | boeconnect | no |
| Cheatham | Cheatham County | County Commission | custom_pdf | no |
| Cheatham | Ashland City | Board of Mayor and Aldermen | custom_other | no |
| Cheatham | Cheatham County | Board of Education | boeconnect | no |
| Putnam | Putnam County | County Commission | custom_pdf | no |
| Putnam | City of Cookeville | City Council | civicengage | no |
| Putnam | Town of Monterey | Board of Mayor and Aldermen | custom_other | no |
| Putnam | City of Baxter | Board of Mayor and Councilmen | custom_pdf | no |
| Putnam | City of Algood | City Council | custom_pdf | no |
| Putnam | Putnam County | Board of Education | custom_pdf | no |

## What this means for prioritizing adapter work

- **CivicEngage (CivicPlus)** covers the largest single chunk of pilot
  jurisdictions (9 of 32). One working adapter here covers the most ground.
- **BoardDocs** and **BOEconnect** together cover most school boards in the
  pilot. Neither publishes a feed; both need HTML/JSON scraping.
- **CivicClerk** is emerging (Smyrna, Portland) and has a documented-ish
  per-event ICS export — a good second target after CivicEngage.
- **Mt. Juliet (Wilson County)** is the one jurisdiction that looks like it's
  already on Legistar, which this project can already talk to via the public
  Legistar Web API (`scraper/platforms/legistar.py`) with zero new code —
  just needs the client name confirmed live.
- Roughly half the jurisdictions (both county commissions, most small towns)
  have no recognized vendor platform at all and will need PDF/HTML scraping
  or ongoing hand-entry (`platform: manual`) — there's no shortcut for those.
