"""
Latvian Kayak Water Level Scraper
Fetches hydrological data from LVĢMC and outputs data.json for the map frontend.
"""

import json
import requests
from datetime import datetime, timezone, timedelta

STATIONS_URL = "https://videscentrs.lvgmc.lv/data/pris_stations"
OBSERVATIONS_URL = "https://videscentrs.lvgmc.lv/data/pris_observations"
OUTPUT_FILE = "data.json"

# Latvian timezone (EET = UTC+2, EEST = UTC+3)
LV_TZ = timezone(timedelta(hours=2))


def fetch_stations():
    """Fetch all station metadata from the LVĢMC API."""
    resp = requests.get(STATIONS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_observations(station_id, date_from, date_to):
    """Fetch observations for a specific station within a date range."""
    params = {
        "station_id": station_id,
        "date_from": date_from,
        "date_to": date_to,
    }
    resp = requests.get(OBSERVATIONS_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extract_water_level(observations):
    """
    Extract the most recent water level data (category 'wlask') from observations.
    Returns a dict with current observation and forecast data, or None if not found.
    """
    # Filter to water level category only
    wlask_records = [o for o in observations if o.get("category") == "wlask"]

    if not wlask_records:
        return None

    # Sort by event_date descending to get the latest record with v_actual
    wlask_records.sort(key=lambda x: x.get("event_date", ""), reverse=True)

    # Find the latest record with an actual observation
    actual_record = None
    for rec in wlask_records:
        if rec.get("v_actual") is not None:
            actual_record = rec
            break

    if actual_record is None:
        return None

    # Get forecast data from the latest record (may differ from actual observation date)
    forecast_record = wlask_records[0]

    return {
        "v_actual": actual_record["v_actual"],
        "observation_date": actual_record.get("event_date"),
        "forecast_median": forecast_record.get("v_mean"),
        "forecast_low": forecast_record.get("v_5"),
        "forecast_high": forecast_record.get("v_95"),
    }


def main():
    print("🌊 Fetching station metadata...")
    all_stations = fetch_stations()

    # Filter to enabled, publicly visible stations
    stations = [
        s for s in all_stations
        if s.get("is_visible_public") and s.get("is_enabled")
    ]
    print(f"   Found {len(stations)} active stations")

    # Date range: yesterday and today (to ensure we get the latest observation)
    now = datetime.now(LV_TZ)
    date_to = now.strftime("%Y-%m-%d")
    date_from = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    results = []
    errors = 0

    for i, station in enumerate(stations, 1):
        station_id = station["id"]
        name = station["name"]
        river = station.get("water_object", "")
        display_name = f"{river} — {name}" if river else name
        elevation = station.get("elevation")

        print(f"   [{i}/{len(stations)}] {display_name}...", end=" ")

        try:
            observations = fetch_observations(station_id, date_from, date_to)
            wl = extract_water_level(observations)

            if wl is None or elevation is None:
                print("⚠ no water level data")
                errors += 1
                continue

            actual_depth = round(wl["v_actual"] - elevation, 2)

            # Calculate forecast depths (relative to zero mark)
            forecast_median_depth = None
            forecast_low_depth = None
            forecast_high_depth = None

            if wl.get("forecast_median") is not None:
                forecast_median_depth = round(wl["forecast_median"] - elevation, 2)
            if wl.get("forecast_low") is not None:
                forecast_low_depth = round(wl["forecast_low"] - elevation, 2)
            if wl.get("forecast_high") is not None:
                forecast_high_depth = round(wl["forecast_high"] - elevation, 2)

            entry = {
                "name": name,
                "river": river,
                "display_name": display_name,
                "lat": station.get("lat"),
                "lon": station.get("lon"),
                "elevation": elevation,
                "current_observation": wl["v_actual"],
                "actual_depth_m": actual_depth,
                "actual_depth_cm": round(actual_depth * 100),
                "forecast_median": wl.get("forecast_median"),
                "forecast_low": wl.get("forecast_low"),
                "forecast_high": wl.get("forecast_high"),
                "forecast_median_depth": forecast_median_depth,
                "forecast_low_depth": forecast_low_depth,
                "forecast_high_depth": forecast_high_depth,
                "observation_date": wl.get("observation_date"),
                "warning_level": station.get("warning_level", "good"),
                "is_sea_station": station.get("is_sea_station", False),
            }
            results.append(entry)
            print(f"✓ depth={actual_depth}m ({round(actual_depth * 100)}cm)")

        except Exception as e:
            print(f"✗ error: {e}")
            errors += 1

    # Build output
    output = {
        "last_updated": now.isoformat(),
        "station_count": len(results),
        "stations": sorted(results, key=lambda x: x["display_name"]),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(results)} stations to {OUTPUT_FILE}")
    if errors:
        print(f"⚠  {errors} stations had no data or errors")


if __name__ == "__main__":
    main()
