
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime
import requests

app = FastAPI(
    title       = "AuraSense API",
    description = "Live pollution monitoring for South India",
    version     = "1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WAQI_TOKEN = os.environ.get("WAQI_TOKEN")

CITIES = [
    # South India
    {"name": "Chennai",            "waqi_name": "chennai",        "lat": 13.0827, "lon": 80.2707},
    {"name": "Bengaluru",          "waqi_name": "bengaluru",      "lat": 12.9716, "lon": 77.5946},
    {"name": "Madurai",            "waqi_name": "tuticorin",      "lat": 9.9252,  "lon": 78.1198},
    {"name": "Coimbatore",         "waqi_name": "coimbatore",     "lat": 11.0168, "lon": 76.9558},
    {"name": "Thiruvananthapuram", "waqi_name": "trivandrum",     "lat": 8.5241,  "lon": 76.9366},
    {"name": "Kochi",              "waqi_name": "ernakulam",      "lat": 9.9312,  "lon": 76.2673},
    {"name": "Hyderabad",          "waqi_name": "hyderabad",      "lat": 17.3850, "lon": 78.4867},
    {"name": "Mysuru",             "waqi_name": "india/mysuru/hebbal-1st-stage", "lat": 12.2958, "lon": 76.6394},
    {"name": "Visakhapatnam",      "waqi_name": "india/visakhapatnam/gvm-corporation", "lat": 17.72,   "lon": 83.3},
    {"name": "Vijayawada",         "waqi_name": "vijayawada",     "lat": 16.5062, "lon": 80.6480},

    # International
    {"name": "London",             "waqi_name": "london",         "lat": 51.5074, "lon": -0.1278},
    {"name": "Dubai",              "waqi_name": "dubai",          "lat": 25.2048, "lon": 55.2708},
    {"name": "Singapore",          "waqi_name": "singapore",      "lat": 1.3521,  "lon": 103.8198},
    {"name": "Sydney",             "waqi_name": "sydney",         "lat": -33.8688,"lon": 151.2093},
    {"name": "Toronto",            "waqi_name": "toronto",        "lat": 43.6532, "lon": -79.3832},
    {"name": "Paris",              "waqi_name": "paris",          "lat": 48.8566, "lon": 2.3522},
    {"name": "Tokyo",              "waqi_name": "tokyo",          "lat": 35.6762, "lon": 139.6503},
    {"name": "Kuala Lumpur",       "waqi_name": "kuala-lumpur",   "lat": 3.1390,  "lon": 101.6869},
    {"name": "Colombo",            "waqi_name": "colombo",        "lat": 6.9271,  "lon": 79.8612},
    {"name": "New York",           "waqi_name": "new-york",       "lat": 40.7128, "lon": -74.0060},
    {"name": "Berlin",             "waqi_name": "berlin",         "lat": 52.5200, "lon": 13.4050},
]

def get_aqi_condition(aqi):
    if aqi <= 50:
        return "Good 🟢"
    elif aqi <= 100:
        return "Moderate 🔵"
    elif aqi <= 150:
        return "Poor 🟠"
    elif aqi <= 300:
        return "Hazardous 🔴"
    else:
        return "Extremely Hazardous 🔴"

def get_temp_condition(temp):
    if temp <= 30:
        return "Pleasant 🟢"
    elif temp <= 38:
        return "Warm 🔵"
    elif temp <= 44:
        return "Hot 🟠"
    else:
        return "Unbearable 🔴"

def get_humidity_condition(humidity):
    if humidity <= 40:
        return "Dry 🟢"
    elif humidity <= 70:
        return "Comfortable 🟢"
    elif humidity <= 85:
        return "Humid 🟠"
    else:
        return "Very Humid 🔴"

def reverse_geocode(lat, lon):
    try:
        url = (
            f"https://api.bigdatacloud.net/data/reverse-geocode-client"
            f"?latitude={lat}&longitude={lon}&localityLanguage=en"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        city = data.get("city") or data.get("locality")
        return city
    except Exception as e:
        return None

def search_city_waqi(city_name):
    try:
        url = f"https://api.waqi.info/search/?token={WAQI_TOKEN}&keyword={city_name}"
        response = requests.get(url, timeout=5)
        data = response.json()
        if data["status"] == "ok" and len(data["data"]) > 0:
            station = data["data"][0]
            return {
                "name": station["station"]["name"],
                "lat": station["station"]["geo"][0],
                "lon": station["station"]["geo"][1],
                "aqi": station["aqi"],
            }
        return None
    except Exception as e:
        return None

def fetch_aqi_waqi(waqi_name):
    try:
        url      = f"https://api.waqi.info/feed/{waqi_name}/?token={WAQI_TOKEN}"
        response = requests.get(url, timeout=5)
        data     = response.json()
        if data["status"] == "ok":
            raw_aqi = data["data"]["aqi"]
            if isinstance(raw_aqi, str) or raw_aqi == "-":
                return None, "No data ⚪"
            aqi_value = int(raw_aqi)
            condition = get_aqi_condition(aqi_value)
            return aqi_value, condition
        return None, "No data ⚪"
    except Exception as e:
        return None, "Timeout ⚪"


def fetch_weather(lat, lon):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        )
        response = requests.get(url, timeout=10)

        # Check connection
        if response.status_code != 200:
            print(f"Weather API error: {response.status_code}")
            return None, None, None

        data = response.json()

        # Correct way to read Open-Meteo response
        current = data.get("current", {})
        temp = current.get("temperature_2m", None)
        humidity = current.get("relative_humidity_2m", None)
        wind = current.get("wind_speed_10m", None)

        print(f"Weather fetched: temp={temp}, humidity={humidity}, wind={wind}")

        return temp, wind, humidity

    except Exception as e:
        print(f"Weather error: {str(e)}")
        return None, None, None

@app.get("/")
def home():
    return {
        "app"     : "AuraSense",
        "version" : "1.0.0",
        "message" : "Welcome to AuraSense API!",
        "status"  : "Server is running! 🌿"
    }

@app.get("/health")
def health_check():
    return {
        "status"  : "healthy",
        "message" : "AuraSense server is up and running!"
    }

@app.get("/pollution")
def get_all_pollution():
    results   = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for city in CITIES:
        aqi_value, aqi_condition = fetch_aqi_waqi(city["waqi_name"])
        temp, wind, humidity     = fetch_weather(city["lat"], city["lon"])
        city_data = {
            "city" : city["name"],
            "aqi"  : {
                "value"     : aqi_value,
                "condition" : aqi_condition,
            },
            "weather" : {
                "temperature"        : temp,
                "temp_condition"     : get_temp_condition(temp) if temp else None,
                "humidity"           : humidity,
                "humidity_condition" : get_humidity_condition(humidity) if humidity else None,
                "wind_speed"         : wind
            }
        }
        results.append(city_data)
    return {
        "timestamp" : timestamp,
        "source"    : "WAQI + Open-Meteo",
        "cities"    : results
    }

@app.get("/pollution-by-coords")
def get_pollution_by_coords(lat: float, lon: float):
    city_name = reverse_geocode(lat, lon)
    if not city_name:
        return {"error": "Could not determine city from location"}

    result = search_city_waqi(city_name)
    if result:
        aqi_value = None
        aqi_condition = "No data ⚪"
        if result["aqi"] not in ("-", None):
            try:
                aqi_value = int(result["aqi"])
                aqi_condition = get_aqi_condition(aqi_value)
            except ValueError:
                pass

        temp, wind, humidity = fetch_weather(lat, lon)
        return {
            "city": city_name,
            "aqi": {
                "value": aqi_value,
                "condition": aqi_condition,
            },
            "weather": {
                "temperature": temp,
                "temp_condition": get_temp_condition(temp) if temp else None,
                "humidity": humidity,
                "humidity_condition": get_humidity_condition(humidity) if humidity else None,
                "wind_speed": wind
            }
        }

    return {"error": f"No station found for {city_name}"}

@app.get("/pollution/{city_name}")
def get_city_pollution(city_name: str):
    for city in CITIES:
        if city_name.lower() in city["name"].lower():
            aqi_value, aqi_condition = fetch_aqi_waqi(city["waqi_name"])
            temp, wind, humidity     = fetch_weather(city["lat"], city["lon"])
            return {
                "city" : city["name"],
                "aqi"  : {
                    "value"     : aqi_value,
                    "condition" : aqi_condition,
                },
                "weather" : {
                    "temperature"        : temp,
                    "temp_condition"     : get_temp_condition(temp) if temp else None,
                    "humidity"           : humidity,
                    "humidity_condition" : get_humidity_condition(humidity) if humidity else None,
                    "wind_speed"         : wind
                }
            }
        # City not in our fixed list — search WAQI directly
        result = search_city_waqi(city_name)
        if result:
            aqi_value = None
            aqi_condition = "No data ⚪"
            if result["aqi"] not in ("-", None):
                try:
                    aqi_value = int(result["aqi"])
                    aqi_condition = get_aqi_condition(aqi_value)
                except ValueError:
                    pass

            temp, wind, humidity = fetch_weather(result["lat"], result["lon"])
            return {
                "city": result["name"],
                "aqi": {
                    "value": aqi_value,
                    "condition": aqi_condition,
                },
                "weather": {
                    "temperature": temp,
                    "temp_condition": get_temp_condition(temp) if temp else None,
                    "humidity": humidity,
                    "humidity_condition": get_humidity_condition(humidity) if humidity else None,
                    "wind_speed": wind
                }
            }

        return {"error": f"City '{city_name}' not found"}

@app.get("/test-weather")

def test_weather():
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude=13.0827"
            f"&longitude=80.2707"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        )
        response = requests.get(url, timeout=5)
        print("Status code:", response.status_code)
        print("Raw response:", response.json())
        return response.json()
    except Exception as e:
        return {"error": str(e)}
