# Time Since Last Crash

A real-time traffic collision tracker for Metro Vancouver. Monitors EMS dispatch data from [PulsePoint](https://www.pulsepoint.org/) and displays how long it's been since the last crash on every street — think "days since last accident" signs, but organized by street.

Data collection started March 8, 2026, with scrapes running roughly every 30 minutes via GitHub Actions.

## How It Works

```
PulsePoint BC EMS Feed
        ↓
  scrape.py (GitHub Actions, ~30 min)
        ↓
  Filter Metro Vancouver collisions, deduplicate, normalize
        ↓
  Write to JSON files (incidents, street index, per-street details)
        ↓
  Commit to repo → POST /api/revalidate
        ↓
  Next.js regenerates pages via on-demand ISR
```

There's no database. All data lives as JSON files committed directly to the repo, which gives free version history and keeps infrastructure minimal.

### Scraping

`scripts/scrape.py` uses Playwright to launch a headless browser (PulsePoint is JS-rendered, so a simple HTTP request won't work). It:

1. Loads the PulsePoint feed in a Pacific-timezone browser context
2. Parses the JS-rendered incident table with BeautifulSoup
3. Filters for traffic collisions in 24 Metro Vancouver municipalities
4. Deduplicates — skips any incident within 2 hours of an existing one at the same location
5. Normalizes street names into URL-friendly slugs
6. Stores all timestamps in UTC for consistent handling across timezones
7. Writes to three JSON files: `data/incidents.json` (all incidents), `data/streets.json` (street index), and `data/streets/{slug}.json` (per-street history)

### Frontend

Built with Next.js (App Router) and Tailwind CSS. Pages are statically generated at build time and revalidated on-demand when new data is scraped, with fallback ISR timers as a safety net.

**Pages:**

- **Home (`/`)** — Top 50 streets ranked by total crash count
- **Recent (`/recent`)** — All streets sorted by most recent crash, with client-side search
- **Street detail (`/{slug}`)** — Live ticking timer since last crash, full incident history, and average period between crashes

**Key components:**

- `LiveClock` — Client-side timer that ticks every second, showing elapsed time since the last crash (hydration-safe with `suppressHydrationWarning`)
- `LocalDateTime` — Converts stored UTC timestamps to the visitor's local timezone
- `StreetSearch` — Client-side filtering across all streets
- `StreetTable` — Reusable table showing street name, last crash time, and total count

In production, data is fetched from GitHub Raw URLs so the site doesn't need to bundle the full data directory. In local dev, it reads from the filesystem.

## Data Format

Each incident looks like:

```json
{
  "id": "2026-03-09T22:21:00Z_mt-seymour-pkwy_roche-point-dr",
  "timestamp": "2026-03-09T22:21:00Z",
  "scrapedAt": "2026-03-09T22:41:19Z",
  "address": "MT SEYMOUR PKWY & ROCHE POINT DR",
  "city": "North Vancouver",
  "streets": ["mt-seymour-pkwy", "roche-point-dr"],
  "streetNames": ["Mt Seymour Pkwy", "Roche Point Dr"]
}
```

The street index (`streets.json`) maps each slug to its name, last incident time, and total count. Individual street files include the full incident history for that street.

## Project Structure

```
app/                    Next.js App Router pages & API
  [slug]/               Street detail pages (statically generated)
  recent/               Recent crashes page
  api/revalidate/       On-demand ISR endpoint
components/             React components (LiveClock, StreetTable, etc.)
lib/                    Data fetching, time formatting, TypeScript types
data/                   JSON data files (incidents, streets, per-street)
scripts/                Python scraping & auditing scripts
```

## Setup

### Site

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Scraper

```bash
pip install -r scripts/requirements.txt
playwright install chromium
python scripts/scrape.py
```

## Environment Variables

| Variable             | Purpose                                                         |
| -------------------- | --------------------------------------------------------------- |
| `GITHUB_REPO`        | `owner/repo` — used to fetch data from GitHub Raw in production |
| `GITHUB_BRANCH`      | Branch to fetch data from (defaults to `main`)                  |
| `REVALIDATION_TOKEN` | Bearer token for the `/api/revalidate` endpoint                 |

## Tech Stack

- **Next.js 16** with App Router, React 19, TypeScript
- **Tailwind CSS 4** with dark mode
- **Python 3** with Playwright + BeautifulSoup for scraping
- **Vercel** for hosting (ISR)
- **GitHub Actions** for scheduled scrapes
