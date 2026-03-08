"""
scrape.py – Fetch traffic collision incidents from PulsePoint (BC EMS)
and append new Metro Vancouver incidents to the local JSON data files.

Uses Playwright (headless Chromium) to load the page, waits for the
JS-rendered table, then scrapes each row's inner text directly.

Exits 0 always. Prints a summary line used by the GitHub Actions workflow
to decide whether to commit.
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FEED_URL = "https://web.pulsepoint.org/?agencies=EMS1201"
INCIDENT_TYPE_FILTER = "traffic collision"

# Metro Vancouver municipality names as they appear in PulsePoint location data.
METRO_CITIES = {
    "Vancouver",
    "Richmond",
    "Surrey",
    "Burnaby",
    "North Vancouver",
    "West Vancouver",
    "Coquitlam",
    "Port Coquitlam",
    "Port Moody",
    "Langley",
    "Delta",
    "New Westminster",
    "Maple Ridge",
    "Pitt Meadows",
    "White Rock",
    "Abbotsford",
    "Mission",
    "Chilliwack",
    "Tsawwassen",
    "Anmore",
    "Belcarra",
    "Lions Bay",
}

DATA_DIR = Path(__file__).parent.parent / "data"
INCIDENTS_FILE = DATA_DIR / "incidents.json"
STREETS_INDEX_FILE = DATA_DIR / "streets.json"
STREETS_DIR = DATA_DIR / "streets"

PACIFIC = ZoneInfo("America/Vancouver")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def title_case(text: str) -> str:
    return " ".join(w.capitalize() for w in text.strip().split())


def parse_streets(address: str) -> tuple[list[str], list[str]]:
    """
    Split an intersection address on ' & ' to get 1 or 2 street names.
    Returns (slugs, display_names).
    """
    parts = [s.strip() for s in address.split(" & ") if s.strip()]
    slugs = [slugify(p) for p in parts[:2]]
    names = [title_case(p) for p in parts[:2]]
    return slugs, names


def make_incident_id(iso_ts: str, slugs: list[str]) -> str:
    slug_part = "_".join(s[:30] for s in slugs[:2]) if slugs else "unknown"
    return f"{iso_ts}_{slug_part}"


def load_json(path: Path, default):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Fetch via Playwright – wait for rendered table, scrape rows
# ---------------------------------------------------------------------------

# Selectors (verified against PulsePoint DOM structure)
# Each row has two <td> cells:
#   td:nth-child(1) – incident type, time, status/duration, unit codes
#   td:nth-child(2) – full address  (may be empty; some layouts combine into td 1)
# We read the full row text and parse it with regex as a reliable fallback.
_TIME_RE = re.compile(
    r"((?:yesterday\s+)?\d{1,2}:\d{2}\s+[ap]m)",
    re.IGNORECASE,
)
_ADDR_AFTER_DURATION_RE = re.compile(
    r"(?:closed\s+-\s+duration\s+[\dhmHM\s]+|active)\s+(.*)",
    re.IGNORECASE,
)


def fetch_incidents(scrape_dt: datetime) -> list[dict]:
    """
    Launch headless Chromium, wait for the PulsePoint table to render,
    then read each row's inner text and parse it.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"[scrape] Loading {FEED_URL}")
        page.goto(FEED_URL, timeout=60_000)

        # Wait for the JS-rendered incident table
        page.wait_for_selector("table", timeout=30_000)
        # Small extra wait to let all rows finish rendering
        page.wait_for_timeout(2_000)

        rows = page.query_selector_all("table tr")
        print(f"[scrape] Found {len(rows)} table rows")

        row_texts: list[tuple[str, str]] = []
        for row in rows:
            # Try to get address from td:nth-child(2) first for a cleaner value
            td2 = row.query_selector("td:nth-child(2)")
            address_cell = td2.inner_text().strip() if td2 else ""
            full_text = row.inner_text().strip()
            row_texts.append((full_text, address_cell))

        browser.close()

    incidents: list[dict] = []
    for full_text, address_cell in row_texts:
        parsed = _parse_row(full_text, address_cell, scrape_dt)
        if parsed:
            incidents.append(parsed)

    return incidents


def _parse_row(
    full_text: str, address_cell: str, scrape_dt: datetime
) -> dict | None:
    """Parse a single PulsePoint table row into our incident schema."""
    if INCIDENT_TYPE_FILTER not in full_text.lower():
        return None

    # --- Time ---
    time_match = _TIME_RE.search(full_text)
    if not time_match:
        return None
    time_str = time_match.group(1)

    # --- Address ---
    # Prefer the dedicated address cell if available
    if address_cell:
        raw_address = address_cell
        # Strip trailing unit codes (e.g. "249A2N 267P3N") from address cell too
        raw_address = re.sub(r"(\s+[A-Z0-9]{3,})+\s*$", "", raw_address).strip()
    else:
        addr_match = _ADDR_AFTER_DURATION_RE.search(full_text)
        if not addr_match:
            return None
        raw_address = addr_match.group(1).strip()
        raw_address = re.sub(r"(\s+[A-Z0-9]{3,})+\s*$", "", raw_address).strip()

    if not raw_address:
        return None

    # --- City ---
    # Address format: "STREET [& STREET], CITY, BC"
    # The city is the second-to-last comma-separated token
    addr_parts = [p.strip() for p in raw_address.split(",")]
    city_raw = addr_parts[-2].strip() if len(addr_parts) >= 3 else (
        addr_parts[-1].strip() if len(addr_parts) == 2 else ""
    )
    city_norm = title_case(city_raw)

    # Street portion is everything before the city
    street_part = ",".join(addr_parts[:-2]).strip() if len(addr_parts) > 2 else addr_parts[0].strip()

    if city_norm not in METRO_CITIES:
        return None

    slugs, names = parse_streets(street_part)
    if not slugs:
        return None

    # --- Timestamp ---
    ts = _parse_time_str(time_str, scrape_dt)
    iso_ts = ts.strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "id": make_incident_id(iso_ts, slugs),
        "timestamp": iso_ts,
        "scrapedAt": scrape_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "address": street_part,
        "city": city_norm,
        "streets": slugs,
        "streetNames": names,
    }


def _parse_time_str(time_str: str, scrape_dt: datetime) -> datetime:
    time_str = time_str.strip()
    date = scrape_dt.date()
    if time_str.lower().startswith("yesterday"):
        date = (scrape_dt - timedelta(days=1)).date()
        time_str = time_str[len("yesterday"):].strip()
    t = datetime.strptime(time_str, "%I:%M %p").time()
    return datetime(date.year, date.month, date.day, t.hour, t.minute, tzinfo=PACIFIC)


# ---------------------------------------------------------------------------
# Data writers
# ---------------------------------------------------------------------------


def update_data_files(new_incidents: list[dict]) -> int:
    all_incidents: list[dict] = load_json(INCIDENTS_FILE, [])
    streets_index: dict = load_json(STREETS_INDEX_FILE, {})

    existing_ids = {inc["id"] for inc in all_incidents}
    added = 0

    for inc in new_incidents:
        if inc["id"] in existing_ids:
            continue

        all_incidents.append(inc)
        existing_ids.add(inc["id"])
        added += 1

        for slug, name in zip(inc["streets"], inc["streetNames"]):
            street_file = STREETS_DIR / f"{slug}.json"
            street_data = load_json(
                street_file,
                {"slug": slug, "name": name, "incidents": [], "lastIncident": None, "count": 0},
            )

            street_data["incidents"].append(
                {
                    "id": inc["id"],
                    "timestamp": inc["timestamp"],
                    "address": inc["address"],
                    "city": inc["city"],
                    "streets": inc["streets"],
                    "streetNames": inc["streetNames"],
                }
            )
            street_data["incidents"].sort(key=lambda x: x["timestamp"], reverse=True)
            street_data["lastIncident"] = street_data["incidents"][0]["timestamp"]
            street_data["name"] = name
            street_data["count"] = len(street_data["incidents"])

            save_json(street_file, street_data)

            streets_index[slug] = {
                "name": name,
                "slug": slug,
                "lastIncident": street_data["lastIncident"],
                "count": street_data["count"],
            }

    if added > 0:
        all_incidents.sort(key=lambda x: x["timestamp"], reverse=True)
        save_json(INCIDENTS_FILE, all_incidents)
        save_json(STREETS_INDEX_FILE, streets_index)

    return added


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    scrape_dt = datetime.now(tz=PACIFIC)
    print(f"[scrape] Starting at {scrape_dt.isoformat()}")

    try:
        fetched = fetch_incidents(scrape_dt)
    except Exception as exc:
        print(f"[scrape] ERROR fetching: {exc}", file=sys.stderr)
        sys.exit(0)

    print(f"[scrape] Found {len(fetched)} Metro Vancouver incidents from feed")

    added = update_data_files(fetched)
    print(f"[scrape] NEW_INCIDENTS={added}")


if __name__ == "__main__":
    main()
from bs4 import BeautifulSoup
