import json
import requests
from datetime import datetime

TARGET_URL = "https://videscentrs.lvgmc.lv/data/hymer_overview"
def scrape_url():
    """
    Fetches the JSON API, and attempts to extract the required data for all stations.
    """
    print(f"🌊 Fetching data from: {TARGET_URL}")
    response = requests.get(TARGET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    response.raise_for_status()

    # The new API provides a list of dictionary objects
    data = response.json()
    
    results = []
    
    for station_data in data:
        name = station_data.get("name")
        lat = station_data.get("lat")
        lon = station_data.get("lon")
        
        # Only include stations that have coordinates
        if lat is None or lon is None:
            continue
            
        # Filter out stations in the sea or gulf
        if "Baltijas jūra" in name or "Rīgas līcis" in name:
            print(f"   Skipping coastal station: {name}")
            continue
            
        print(f"   Analyzing station: {name}")
        
        # Initialize default None values
        actual_depth = None
        water_temp = None
        update_time = None
        
        # We look for "Ūdens līmenis" and "Ūdens temperatūra" in the 'ts' (time series) array
        time_series = station_data.get("ts", [])
        for ts in time_series:
            ts_name = ts.get("name", "")
            if ts_name == "Ūdens līmenis":
                try:
                    actual_depth = float(ts.get("value"))
                    last_dt = ts.get("last_date", "")
                    if last_dt:
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
        
        results.append({
            "name": name,
            "lat": lat,
            "lon": lon,
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
