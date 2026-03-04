import json
import requests
from datetime import datetime

TARGET_URL = "https://videscentrs.lvgmc.lv/data/hymer_overview"
# Defining the targeted stations and their rough coordinates for Leaflet map mapping.
STATIONS = [
    {"name": "Amata, Melturi", "display_name": "Amata-Melturi", "lat": 57.2273, "lon": 25.2263},
    {"name": "Salaca, Mazsalaca", "display_name": "Salaca-Mazsalaca", "lat": 57.8643, "lon": 25.0454},
    {"name": "Svēte, Ūziņi", "display_name": "Svēte-Ūziņi", "lat": 56.5492, "lon": 23.5510}
]

def scrape_url():
    """
    Fetches the JSON API, and attempts to extract the required data for the stations.
    """
    print(f"🌊 Fetching data from: {TARGET_URL}")
    response = requests.get(TARGET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    response.raise_for_status()

    # The new API provides a list of dictionary objects
    data = response.json()
    
    results = []
    
    for station in STATIONS:
        station_name = station["name"]
        display_name = station["display_name"]
        print(f"   Analyzing station: {display_name}")
        
        # Initialize default None values
        actual_depth = None
        water_temp = None
        update_time = None
        
        # Find the station in the API response
        station_data = next((item for item in data if item.get("name") == station_name), None)
        
        if station_data:
            # We look for "Ūdens līmenis" and "Ūdens temperatūra" in the 'ts' (time series) array
            time_series = station_data.get("ts", [])
            for ts in time_series:
                ts_name = ts.get("name", "")
                if ts_name == "Ūdens līmenis":
                    try:
                        actual_depth = float(ts.get("value"))
                        # Use the timestamp from the depth reading
                        # E.g. "2026-03-04 19:20:00" -> format if needed, but string works well
                        last_dt = ts.get("last_date", "")
                        if last_dt:
                            # Try formatting to the old format if we want consistency: "DD.MM.YYYY HH:MM"
                            try:
                                dt = datetime.strptime(last_dt, "%Y-%m-%d %H:%M:%S")
                                update_time = dt.strftime("%d.%m.%Y %H:%M")
                            except ValueError:
                                update_time = last_dt
                    except (ValueError, TypeError):
                        pass
                elif ts_name == "Ūdens temperatūra":
                    try:
                        water_temp = float(ts.get("value"))
                    except (ValueError, TypeError):
                        pass
        else:
            print(f"   ⚠️ Station '{station_name}' not found in API response.")
        
        results.append({
            "name": display_name,
            "lat": station["lat"],
            "lon": station["lon"],
            "actual_depth_m": actual_depth,
            "water_temperature_c": water_temp,
            "update_time": update_time
        })
        
        print(f"✓ Depth: {actual_depth}m, Temp: {water_temp}°C, Time: {update_time}")

    return {
        "last_updated": datetime.now().isoformat(),
        "station_count": len(results),
        "stations": results
    }

def main():
    try:
        data = scrape_url()
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {data['station_count']} stations to data.json")
    except Exception as e:
        print(f"❌ Scraper failed: {e}")

if __name__ == "__main__":
    main()
