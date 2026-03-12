"""
scrape.py – Fetch traffic collision incidents from PulsePoint (BC EMS)
and append new Metro Vancouver incidents to the local JSON data files.

Uses Playwright (headless Chromium) to load the page, waits for the
JS-rendered table, then extracts PulsePoint incident IDs from the React
fiber tree on each table row for definitive deduplication.  No clicking
is required — all data is read from the DOM in a single JS call.

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


def parse_streets(address: str, city: str) -> tuple[list[str], list[str], list[str]]:
    """
    Split an intersection address on ' & ' to get 1 or 2 street names.
    Returns (city_namespaced_slugs, street_only_slugs, display_names).
    City-namespaced slugs have the form "city-slug/street-slug".
    """
    city_slug = slugify(city)
    parts = [s.strip() for s in address.split(" & ") if s.strip()]
    street_slugs = [slugify(p) for p in parts[:2]]
    namespaced_slugs = [f"{city_slug}/{s}" for s in street_slugs]
    names = [title_case(p) for p in parts[:2]]
    return namespaced_slugs, street_slugs, names


def make_incident_id(iso_ts: str, slugs: list[str]) -> str:
    slug_part = "_".join(s[:60] for s in slugs[:2]) if slugs else "unknown"
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
# Fetch via Playwright – extract PulsePoint IDs for deduplication
# ---------------------------------------------------------------------------

# PulsePoint renders a single-column incident table (tables[1] on the page).
# Each row inner text has the pipe-separated format:
#   "Traffic Collision | 12:19 a.m. | ADDRESS, CITY, BC [| unit…]"
#   "Traffic Collision | Yesterday 11:15 p.m. | CLOSED - DURATION 23M | ADDRESS, CITY, BC [| unit…]"
# Section-header rows ("Active | (6)", "Recent | (56)") are filtered out.
#
# PulsePoint IDs are extracted from React's internal fiber tree on each <tr>.
# The TableRow component (at fiber ancestor depth 2) stores the numeric
# PulsePoint incident ID as its React key.  This avoids any clicking.

_TIME_RE = re.compile(
    r"((?:yesterday\s+)?\d{1,2}:\d{2}\s*[ap]\.?m\.?)",
    re.IGNORECASE,
)

# JavaScript snippet injected once to extract PP IDs from all rows at once.
# Returns a list of {index, ppId, text} for every <tr> in the incident table.
_EXTRACT_PP_IDS_JS = """() => {
    const table = document.querySelectorAll('table')[1];
    if (!table) return [];
    const rows = table.querySelectorAll('tr');
    const results = [];

    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const text = row.innerText || '';
        let ppId = null;

        // Walk up the React fiber tree to find the TableRow component key.
        const fiberKey = Object.keys(row).find(k =>
            k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$')
        );
        if (fiberKey) {
            let current = row[fiberKey];
            // TableRow is typically at depth 2 (tr → Styled(tr) → TableRow),
            // but search up to 5 levels to be safe.
            for (let depth = 0; depth < 5 && current; depth++) {
                if (current.key && /^\\d{5,}$/.test(String(current.key))) {
                    ppId = String(current.key);
                    break;
                }
                current = current.return;
            }
        }
        results.push({index: i, ppId: ppId, text: text});
    }
    return results;
}"""


def fetch_incidents(
    scrape_dt: datetime,
    known_pp_ids: set[str],
) -> list[dict]:
    """
    Launch headless Chromium, parse the PulsePoint feed table.
    Extracts PulsePoint incident IDs from the React fiber tree on each row
    (no clicking needed). Rows whose PulsePoint ID is already known are
    skipped immediately.
    """
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(timezone_id="America/Vancouver")
        page = context.new_page()

        print(f"[scrape] Loading {FEED_URL}")
        page.goto(FEED_URL, timeout=60_000)
        page.wait_for_selector("table", timeout=30_000)
        page.wait_for_timeout(2_000)

        # Extract all row texts and PP IDs in a single JS call
        row_data = page.evaluate(_EXTRACT_PP_IDS_JS)
        browser.close()

    print(f"[scrape] Found {len(row_data)} rows in incident table")

    incidents: list[dict] = []
    skipped_known = 0
    skipped_no_id = 0

    for entry in row_data:
        text = entry["text"]
        pp_id = entry["ppId"]

        if INCIDENT_TYPE_FILTER not in text.lower():
            continue

        # Skip already-known incidents by PulsePoint ID
        if pp_id and pp_id in known_pp_ids:
            skipped_known += 1
            continue

        parsed = _parse_row(text, scrape_dt)
        if not parsed:
            continue

        if pp_id:
            parsed["pulsePointId"] = pp_id
        else:
            skipped_no_id += 1
            print(f"[scrape] WARNING: No PP ID for {parsed['address']}, {parsed['city']}")

        incidents.append(parsed)

    pp_id_count = sum(1 for e in row_data if e["ppId"])
    collision_count = sum(1 for e in row_data if INCIDENT_TYPE_FILTER in e["text"].lower())
    print(f"[scrape] {collision_count} traffic collisions, {pp_id_count} PP IDs extracted")
    print(f"[scrape] Skipped {skipped_known} known, {skipped_no_id} without PP ID, {len(incidents)} candidates")

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

    slugs, street_slugs, names = parse_streets(street_part, city_norm)
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
    result = datetime(date.year, date.month, date.day, t.hour, t.minute, tzinfo=PACIFIC)
    # If the computed time is in the future, it means PulsePoint showed a
    # previous-evening incident without a "Yesterday" prefix (common when
    # scraping shortly after midnight). Roll back one day.
    if result > scrape_dt:
        result -= timedelta(days=1)
    return result


# ---------------------------------------------------------------------------
# Data writers
# ---------------------------------------------------------------------------


def update_data_files(new_incidents: list[dict]) -> int:
    all_incidents: list[dict] = load_json(INCIDENTS_FILE, [])
    streets_index: dict = load_json(STREETS_INDEX_FILE, {})

    existing_ids = {inc["id"] for inc in all_incidents}
    existing_pp_ids = {inc["pulsePointId"] for inc in all_incidents if inc.get("pulsePointId")}
    added = 0

    def _is_near_duplicate(inc: dict) -> bool:
        """
        Fallback dedup for incidents that lack a PulsePoint ID.
        Only used during the transition period while historical incidents
        don't yet have PulsePoint IDs.
        """
        new_ts = datetime.fromisoformat(inc["timestamp"])
        new_slugs = set(inc["streets"])

        for existing in all_incidents:
            if existing["city"] != inc["city"]:
                continue
            if set(existing["streets"]) != new_slugs:
                continue

            existing_ts = datetime.fromisoformat(existing["timestamp"])
            if abs((new_ts - existing_ts).total_seconds()) < 90000:  # 25 hours
                return True

        return False

    for inc in new_incidents:
        # Primary dedup: PulsePoint ID (definitive)
        pp_id = inc.get("pulsePointId")
        if pp_id and pp_id in existing_pp_ids:
            continue

        # Secondary dedup: our generated ID
        if inc["id"] in existing_ids:
            continue

        # Fallback dedup: near-duplicate heuristic for incidents without PP ID
        if not pp_id and _is_near_duplicate(inc):
            print(f"[scrape] Skipping near-duplicate (no PP ID): {inc['id']}")
            continue

        all_incidents.append(inc)
        existing_ids.add(inc["id"])
        if pp_id:
            existing_pp_ids.add(pp_id)
        added += 1

        for slug, name in zip(inc["streets"], inc["streetNames"]):
            # slug is city-namespaced: "city-slug/street-slug"
            street_file = STREETS_DIR / f"{slug}.json"
            street_data = load_json(
                street_file,
                {"slug": slug, "name": name, "city": inc["city"], "incidents": [], "lastIncident": None, "count": 0},
            )

            incident_entry = {
                "id": inc["id"],
                "timestamp": inc["timestamp"],
                "address": inc["address"],
                "city": inc["city"],
                "streets": inc["streets"],
                "streetNames": inc["streetNames"],
            }
            if pp_id:
                incident_entry["pulsePointId"] = pp_id

            street_data["incidents"].append(incident_entry)
            street_data["incidents"].sort(key=lambda x: x["timestamp"], reverse=True)
            street_data["lastIncident"] = street_data["incidents"][0]["timestamp"]
            street_data["name"] = name
            street_data["city"] = inc["city"]
            street_data["count"] = len(street_data["incidents"])

            save_json(street_file, street_data)

            streets_index[slug] = {
                "name": name,
                "slug": slug,
                "city": inc["city"],
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

    # Load known PulsePoint IDs so we can skip already-recorded incidents
    # without needing to click into them.
    existing = load_json(INCIDENTS_FILE, [])
    known_pp_ids = {inc["pulsePointId"] for inc in existing if inc.get("pulsePointId")}
    print(f"[scrape] {len(existing)} existing incidents, {len(known_pp_ids)} with PulsePoint IDs")

    try:
        fetched = fetch_incidents(scrape_dt, known_pp_ids)
    except Exception as exc:
        print(f"[scrape] ERROR fetching: {exc}", file=sys.stderr)
        sys.exit(0)

    print(f"[scrape] {len(fetched)} candidate incidents from feed")

    added = update_data_files(fetched)
    print(f"[scrape] NEW_INCIDENTS={added}")


if __name__ == "__main__":
    main()
