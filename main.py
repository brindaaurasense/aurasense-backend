from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, select
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import timedelta

WAQI_TOKEN = os.environ.get("WAQI_TOKEN")

DB_HOST     = os.environ.get("DB_HOST")
DB_PORT     = os.environ.get("DB_PORT")
DB_NAME     = os.environ.get("DB_NAME")
DB_USER     = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "aurasense-dev-secret-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days

class User(Base):
    __tablename__ = "users"

    id                      = Column(Integer, primary_key=True, index=True)
    email                   = Column(String, unique=True, index=True, nullable=False)
    hashed_password         = Column(String, nullable=False)
    favorite_cities         = Column(String, default="")
    pollution_alerts_opt_in = Column(Boolean, default=False)
    created_at              = Column(DateTime, default=lambda: datetime.now())

class SignupRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(email: str) -> str:
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": email, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title       = "AuraSense API",
    description = "Live pollution monitoring for South India",
    version     = "1.0.0",
    lifespan    = lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

async def reverse_geocode(lat, lon):
    try:
        url = (
            f"https://api.bigdatacloud.net/data/reverse-geocode-client"
            f"?latitude={lat}&longitude={lon}&localityLanguage=en"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
        data = response.json()
        city = data.get("city") or data.get("locality")
        return city
    except Exception as e:
        return None

async def search_city_waqi(city_name):
    try:
        url = f"https://api.waqi.info/search/?token={WAQI_TOKEN}&keyword={city_name}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
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

async def fetch_aqi_waqi(waqi_name):
    try:
        url = f"https://api.waqi.info/feed/{waqi_name}/?token={WAQI_TOKEN}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
        data = response.json()
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

async def fetch_weather(lat, lon):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)

        if response.status_code != 200:
            print(f"Weather API error: {response.status_code}")
            return None, None, None, None

        data = response.json()

        current = data.get("current", {})
        temp = current.get("temperature_2m", None)
        feels_like = current.get("apparent_temperature", None)
        humidity = current.get("relative_humidity_2m", None)
        wind = current.get("wind_speed_10m", None)

        print(f"Weather fetched: temp={temp}, feels_like={feels_like}, humidity={humidity}, wind={wind}")

        return temp, wind, humidity, feels_like

    except Exception as e:
        print(f"Weather error: {str(e)}")
        return None, None, None, None

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
async def get_all_pollution():
    results   = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for city in CITIES:
        aqi_value, aqi_condition = await fetch_aqi_waqi(city["waqi_name"])
        temp, wind, humidity, feels_like = await fetch_weather(city["lat"], city["lon"])
        city_data = {
            "city" : city["name"],
            "aqi"  : {
                "value"     : aqi_value,
                "condition" : aqi_condition,
            },
            "weather" : {
                "temperature"        : temp,
                "feels_like"         : feels_like,
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
async def get_pollution_by_coords(lat: float, lon: float):
    try:
        city_name, (temp, wind, humidity, feels_like) = await asyncio.gather(
            reverse_geocode(lat, lon),
            fetch_weather(lat, lon)
        )

        if not city_name:
            return {"error": "Could not determine city from location"}

        result = await search_city_waqi(city_name)
        if result:
            aqi_value     = None
            aqi_condition = "No data ⚪"
            if result["aqi"] not in ("-", None):
                try:
                    aqi_value     = int(result["aqi"])
                    aqi_condition = get_aqi_condition(aqi_value)
                except ValueError:
                    pass
            return {
                "city"    : city_name,
                "aqi"     : {
                    "value"     : aqi_value,
                    "condition" : aqi_condition,
                },
                "weather" : {
                    "temperature"        : temp,
                    "feels_like"         : feels_like,
                    "temp_condition"     : get_temp_condition(temp) if temp else None,
                    "humidity"           : humidity,
                    "humidity_condition" : get_humidity_condition(humidity) if humidity else None,
                    "wind_speed"         : wind
                }
            }

        nearest_city_map = {
            'srivilliputtur' : 'Madurai',
            'srivilliputhur' : 'Madurai',
            'rajapalayam'    : 'Madurai',
            'virudhunagar'   : 'Madurai',
            'tenkasi'        : 'Madurai',
            'tirunelveli'    : 'Madurai',
            'thoothukudi'    : 'Madurai',
            'dindigul'       : 'Madurai',
            'theni'          : 'Madurai',
            'karur'          : 'Coimbatore',
            'erode'          : 'Coimbatore',
            'tiruppur'       : 'Coimbatore',
            'ooty'           : 'Coimbatore',
            'vellore'        : 'Chennai',
            'kanchipuram'    : 'Chennai',
            'pondicherry'    : 'Chennai',
            'thanjavur'      : 'Madurai',
            'trichy'         : 'Madurai',
            'nagapattinam'   : 'Madurai',
            'salem'          : 'Coimbatore',
            'thrissur'       : 'Kochi',
            'palakkad'       : 'Kochi',
            'kozhikode'      : 'Kochi',
            'kannur'         : 'Kochi',
            'kollam'         : 'Thiruvananthapuram',
            'alappuzha'      : 'Kochi',
            'mysuru'         : 'Bengaluru',
            'mangaluru'      : 'Bengaluru',
            'hubli'          : 'Bengaluru',
            'vijayawada'     : 'Hyderabad',
            'visakhapatnam'  : 'Hyderabad',
            'tirupati'       : 'Hyderabad',
            'guntur'         : 'Hyderabad',
            'warangal'       : 'Hyderabad',
        }

        nearest = nearest_city_map.get(city_name.lower())
        if nearest:
            for city in CITIES:
                if nearest.lower() in city["name"].lower():
                    aqi_value, aqi_condition = await fetch_aqi_waqi(city["waqi_name"])
                    return {
                        "city"    : nearest,
                        "aqi"     : {
                            "value"     : aqi_value,
                            "condition" : aqi_condition,
                        },
                        "weather" : {
                            "temperature"        : temp,
                            "feels_like"         : feels_like,
                            "temp_condition"     : get_temp_condition(temp) if temp else None,
                            "humidity"           : humidity,
                            "humidity_condition" : get_humidity_condition(humidity) if humidity else None,
                            "wind_speed"         : wind
                        }
                    }

        return {"error": f"No station found for {city_name}"}

    except Exception as e:
        return {"error": str(e)}

@app.get("/pollution/{city_name}")
async def get_city_pollution(city_name: str):
    for city in CITIES:
        if city_name.lower() in city["name"].lower():
            aqi_value, aqi_condition = await fetch_aqi_waqi(city["waqi_name"])
            temp, wind, humidity, feels_like = await fetch_weather(city["lat"], city["lon"])
            return {
                "city" : city["name"],
                "aqi"  : {
                    "value"     : aqi_value,
                    "condition" : aqi_condition,
                },
                "weather" : {
                    "temperature"        : temp,
                    "feels_like"         : feels_like,
                    "temp_condition"     : get_temp_condition(temp) if temp else None,
                    "humidity"           : humidity,
                    "humidity_condition" : get_humidity_condition(humidity) if humidity else None,
                    "wind_speed"         : wind
                }
            }

    result = await search_city_waqi(city_name)
    if result:
        aqi_value = None
        aqi_condition = "No data ⚪"
        if result["aqi"] not in ("-", None):
            try:
                aqi_value = int(result["aqi"])
                aqi_condition = get_aqi_condition(aqi_value)
            except ValueError:
                pass

        temp, wind, humidity, feels_like = await fetch_weather(result["lat"], result["lon"])
        return {
            "city": result["name"],
            "aqi": {
                "value": aqi_value,
                "condition": aqi_condition,
            },
            "weather": {
                "temperature": temp,
                "feels_like": feels_like,
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

@app.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == request.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return {"error": "Email already registered"}

        new_user = User(
            email=request.email,
            hashed_password=hash_password(request.password),
        )
        session.add(new_user)
        await session.commit()

        token = create_access_token(request.email)
        return {"access_token": token, "token_type": "bearer"}

@app.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(request.password, user.hashed_password):
            return {"error": "Invalid email or password"}

        token = create_access_token(request.email)
        return {"access_token": token, "token_type": "bearer"}
