import json
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

TARGET_URL = "https://videscentrs.lvgmc.lv/iebuvets/hidrologiska-operativa-informacija"
# Defining the targeted stations and their rough coordinates for Leaflet map mapping.
STATIONS = [
    {"name": "Amata-Melturi", "lat": 57.2273, "lon": 25.2263},
    {"name": "Salaca-Mazsalaca", "lat": 57.8643, "lon": 25.0454},
    {"name": "Svēte-Ūziņi", "lat": 56.5492, "lon": 23.5510}
]

def clean_text(text):
    return text.strip().replace('\xa0', ' ')

def scrape_url():
    """
    Fetches the HTML, and attempts to extract the required data using BeautifulSoup
    and Regex, searching for the specific data labels given.
    """
    print(f"🌊 Fetching data from: {TARGET_URL}")
    response = requests.get(TARGET_URL, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    
    # We will attempt to parse the raw HTML text to find the data dictionary or XHR JSON.
    # If the page includes the data rendered in HTML:
    results = []
    
    for station in STATIONS:
        station_name = station["name"]
        print(f"   Analyzing station: {station_name}")
        
        # We look for the station name in the document
        station_node = soup.find(string=re.compile(station_name))
        
        # Initialize default None values
        actual_depth = None
        water_temp = None
        update_time = None
        
        if station_node:
            # We assume the information is stored in the parent container
            container = station_node.find_parent("div") or station_node.find_parent("tr")
            if container:
                text_content = clean_text(container.get_text())
                
                # Actual Kayaking Depth
                depth_match = re.search(r"Ūdens līmenis virs stacijas nulles atzīmes:\s*([-\d.]+)\s*m", text_content)
                if depth_match:
                    actual_depth = float(depth_match.group(1))
                    
                # Water Temperature
                temp_match = re.search(r"Ūdens temperatūra:\s*([-\d.]+)\s*°C", text_content)
                if temp_match:
                    water_temp = float(temp_match.group(1))
                    
                # Latest Update Time
                time_match = re.search(r"Dati par\s+(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})", text_content)
                if time_match:
                    update_time = time_match.group(1)
        
        # Fallback: Extract XHR JSON dictionary if embedded in a <script> tag:
        if actual_depth is None or water_temp is None:
            json_match = re.search(r"var data = (\{.*?\});", html, re.DOTALL)
            if json_match:
                try:
                    data_dict = json.loads(json_match.group(1))
                    for item in data_dict.get("stations", []):
                        if station_name in item.get("name", ""):
                            actual_depth = item.get("depth", actual_depth)
                            water_temp = item.get("temp", water_temp)
                            update_time = item.get("time", update_time)
                except json.JSONDecodeError:
                    pass
        
        results.append({
            "name": station_name,
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
    data = scrape_url()
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved {data['station_count']} stations to data.json")

if __name__ == "__main__":
    main()
