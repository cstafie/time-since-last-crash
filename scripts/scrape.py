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
from datetime import datetime, timedelta, timezone
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

# PulsePoint renders a single-column incident table (tables[1] on the page).
# Each row inner text has the pipe-separated format:
#   "Traffic Collision | 12:19 a.m. | ADDRESS, CITY, BC [| unit…]"
#   "Traffic Collision | Yesterday 11:15 p.m. | CLOSED - DURATION 23M | ADDRESS, CITY, BC [| unit…]"
# Section-header rows ("Active | (6)", "Recent | (56)") are filtered out.

_TIME_RE = re.compile(
    r"((?:yesterday\s+)?\d{1,2}:\d{2}\s*[ap]\.?m\.?)",
    re.IGNORECASE,
)


def fetch_incidents(scrape_dt: datetime) -> list[dict]:
    """
    Launch headless Chromium, wait for the PulsePoint table to render,
    then read each row's inner text and parse it.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        # Force Pacific time so PulsePoint renders incident times in PST/PDT
        # consistently regardless of the runner's system timezone (e.g. UTC on GH Actions).
        context = browser.new_context(timezone_id="America/Vancouver")
        page = context.new_page()

        print(f"[scrape] Loading {FEED_URL}")
        page.goto(FEED_URL, timeout=60_000)

        # Wait for the JS-rendered incident table
        page.wait_for_selector("table", timeout=30_000)
        # Small extra wait to let all rows finish rendering
        page.wait_for_timeout(2_000)

        tables = page.query_selector_all("table")
        # tables[0] is the keyboard-shortcut table; tables[-1] is the incidents feed
        incident_table = tables[-1] if len(tables) >= 2 else tables[0]
        rows = incident_table.query_selector_all("tr")
        print(f"[scrape] Found {len(rows)} incident rows")

        row_texts = [row.inner_text().strip() for row in rows]
        browser.close()

    incidents: list[dict] = []
    for text in row_texts:
        parsed = _parse_row(text, scrape_dt)
        if parsed:
            incidents.append(parsed)

    return incidents


def _parse_row(full_text: str, scrape_dt: datetime) -> dict | None:
    """Parse a single PulsePoint pipe-delimited row into our incident schema."""
    if INCIDENT_TYPE_FILTER not in full_text.lower():
        return None

    # Each row's inner text has newline-delimited fields:
    #   field[0] = incident type
    #   field[1] = time (e.g. "12:19 a.m." or "Yesterday 11:15 p.m.")
    #   field[2] = address OR "CLOSED - DURATION Xm"
    #   field[3] = address (if field[2] was CLOSED…), otherwise unit code
    #   field[3+] = unit codes
    fields = [f.strip() for f in full_text.splitlines() if f.strip()]

    if len(fields) < 3:
        return None

    # --- Time ---
    time_match = _TIME_RE.search(fields[1])
    if not time_match:
        return None
    time_str = time_match.group(1)

    # --- Address ---
    # If field[2] starts with "CLOSED", the address is in field[3]
    if fields[2].upper().startswith("CLOSED"):
        raw_address = fields[3] if len(fields) > 3 else ""
    else:
        raw_address = fields[2]

    if not raw_address:
        return None

    # --- City ---
    # Format: "STREET [& STREET], CITY, BC"
    addr_parts = [p.strip() for p in raw_address.split(",")]
    if len(addr_parts) < 2:
        return None

    city_raw = addr_parts[-2] if len(addr_parts) >= 3 else addr_parts[-1]
    city_norm = title_case(city_raw)

    street_part = ",".join(addr_parts[:-2]).strip() if len(addr_parts) > 2 else addr_parts[0].strip()

    if city_norm not in METRO_CITIES:
        return None

    slugs, names = parse_streets(street_part)
    if not slugs:
        return None

    # --- Timestamp ---
    ts = _parse_time_str(time_str, scrape_dt)
    # Store as UTC with Z suffix so JavaScript's new Date() parses it correctly
    # in any browser timezone. Display conversion to Pacific happens in the frontend.
    iso_ts = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "id": make_incident_id(iso_ts, slugs),
        "timestamp": iso_ts,
        "scrapedAt": scrape_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    # Normalise "a.m." / "p.m." → "AM" / "PM"
    time_str = re.sub(r"a\.m\.", "AM", time_str, flags=re.IGNORECASE)
    time_str = re.sub(r"p\.m\.", "PM", time_str, flags=re.IGNORECASE)
    time_str = time_str.strip()
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

    def _is_near_duplicate(inc: dict) -> bool:
        """
        True if an existing incident at the same location is within 30 minutes,
        OR if it looks like a day-boundary / DST re-scrape (same address+city,
        same time-of-day within ±5 min, dates differ by exactly 1 day).
        """
        new_ts = datetime.fromisoformat(inc["timestamp"])
        new_slugs = set(inc["streets"])
        new_pacific = new_ts.astimezone(PACIFIC)
        new_minutes_of_day = new_pacific.hour * 60 + new_pacific.minute

        for existing in all_incidents:
            if existing["city"] != inc["city"]:
                continue
            if set(existing["streets"]) != new_slugs:
                continue

            existing_ts = datetime.fromisoformat(existing["timestamp"])
            diff_seconds = abs((new_ts - existing_ts).total_seconds())

            # Direct near-duplicate (within 30 min)
            if diff_seconds < 1800:
                return True

            # Day-boundary / DST duplicate: same address, same time-of-day,
            # dates ~23-25 hours apart (covers the ±1h DST shift over a day boundary)
            if 22 * 3600 <= diff_seconds <= 26 * 3600:
                existing_pacific = existing_ts.astimezone(PACIFIC)
                existing_minutes_of_day = existing_pacific.hour * 60 + existing_pacific.minute
                if abs(new_minutes_of_day - existing_minutes_of_day) <= 5:
                    return True

        return False

    for inc in new_incidents:
        if inc["id"] in existing_ids:
            continue
        if _is_near_duplicate(inc):
            print(f"[scrape] Skipping near-duplicate: {inc['id']}")
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
