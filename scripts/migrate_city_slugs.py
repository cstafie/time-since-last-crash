"""
migrate_city_slugs.py – One-time migration script.

Reads existing flat data/streets/*.json files (which may mix cities),
splits them by city, and writes to data/streets/{city-slug}/{street-slug}.json.
Also rebuilds data/streets.json index and updates incident slug references
in data/incidents.json.

Run once, then commit the migrated data and delete old flat street files.
"""

import json
import re
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
INCIDENTS_FILE = DATA_DIR / "incidents.json"
STREETS_INDEX_FILE = DATA_DIR / "streets.json"
STREETS_DIR = DATA_DIR / "streets"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def load_json(path: Path, default=None):
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    # ---------------------------------------------------------------
    # Step 1: Read all existing flat street files and group by city
    # ---------------------------------------------------------------
    old_street_files = sorted(STREETS_DIR.glob("*.json"))
    print(f"[migrate] Found {len(old_street_files)} old street files")

    # Collect all incidents grouped by (city_slug, street_slug)
    # Key: (city_slug, street_slug) -> { incidents: [...], name, city }
    new_streets: dict[tuple[str, str], dict] = {}

    for sf in old_street_files:
        data = load_json(sf)
        if not data or "incidents" not in data:
            continue

        old_slug = data["slug"]
        for inc in data["incidents"]:
            city = inc.get("city", "")
            if not city:
                print(f"[migrate] WARNING: incident {inc.get('id', '?')} has no city, skipping")
                continue

            city_slug = slugify(city)
            street_slug = old_slug  # keep the original street-only slug

            key = (city_slug, street_slug)
            if key not in new_streets:
                new_streets[key] = {
                    "slug": f"{city_slug}/{street_slug}",
                    "name": data.get("name", ""),
                    "city": city,
                    "incidents": [],
                    "lastIncident": None,
                    "count": 0,
                }

            # Build new city-namespaced slugs for this incident's streets
            new_inc_streets = [f"{city_slug}/{s}" for s in inc.get("streets", [])]

            new_streets[key]["incidents"].append({
                "id": inc["id"],
                "timestamp": inc["timestamp"],
                "address": inc.get("address", ""),
                "city": city,
                "streets": new_inc_streets,
                "streetNames": inc.get("streetNames", []),
            })

    # ---------------------------------------------------------------
    # Step 2: Build a mapping old_slug -> new_slug per city for incidents.json
    # Also build (old_incident_id -> new_streets) for patching incidents.json
    # ---------------------------------------------------------------
    # We need to update each incident's "streets" field in incidents.json

    # ---------------------------------------------------------------
    # Step 3: Finalize street data and write new files
    # ---------------------------------------------------------------
    new_index: dict[str, dict] = {}

    for (city_slug, street_slug), street_data in sorted(new_streets.items()):
        # Sort incidents newest first
        street_data["incidents"].sort(key=lambda x: x["timestamp"], reverse=True)
        street_data["lastIncident"] = street_data["incidents"][0]["timestamp"]
        street_data["count"] = len(street_data["incidents"])

        namespaced_slug = f"{city_slug}/{street_slug}"
        new_file = STREETS_DIR / f"{namespaced_slug}.json"
        save_json(new_file, street_data)
        print(f"[migrate] Wrote {new_file} ({street_data['count']} incidents)")

        new_index[namespaced_slug] = {
            "name": street_data["name"],
            "slug": namespaced_slug,
            "city": street_data["city"],
            "lastIncident": street_data["lastIncident"],
            "count": street_data["count"],
        }

    # ---------------------------------------------------------------
    # Step 4: Update incidents.json — patch each incident's "streets"
    # ---------------------------------------------------------------
    all_incidents: list[dict] = load_json(INCIDENTS_FILE, [])
    patched = 0
    for inc in all_incidents:
        city = inc.get("city", "")
        city_slug = slugify(city)
        old_streets = inc.get("streets", [])
        # Check if already migrated (contains '/')
        if any("/" in s for s in old_streets):
            continue
        new_streets_list = [f"{city_slug}/{s}" for s in old_streets]
        inc["streets"] = new_streets_list
        patched += 1

    if patched > 0:
        save_json(INCIDENTS_FILE, all_incidents)
        print(f"[migrate] Patched {patched} incidents in incidents.json")

    # ---------------------------------------------------------------
    # Step 5: Write new streets.json index
    # ---------------------------------------------------------------
    save_json(STREETS_INDEX_FILE, new_index)
    print(f"[migrate] Wrote streets.json with {len(new_index)} entries")

    # ---------------------------------------------------------------
    # Step 6: Delete old flat street files
    # ---------------------------------------------------------------
    deleted = 0
    for sf in old_street_files:
        sf.unlink()
        deleted += 1
    print(f"[migrate] Deleted {deleted} old flat street files")

    print("[migrate] Done!")


if __name__ == "__main__":
    main()
