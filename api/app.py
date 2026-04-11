"""
NaviTour — Egypt Transport Recommendation API
─────────────────────────────────────────────
Endpoints:
  GET  /health
  GET  /api/stations
  GET  /api/stations/{name}/restaurants
  GET  /api/stations/{name}/places
  GET  /api/bus-stops
  GET  /api/route?start=...&end=...&time=...
  POST /message
  POST /reset
  POST /api/location
  POST /api/users/register         ← login or create user with password
  GET  /api/users/{user_id}
  GET  /api/ratings/{user_id}
  GET  /api/item-ratings
  POST /api/ratings                ← submit or update rating
  GET  /api/recommend/{user_id}
  GET  /api/recommend/{user_id}/places
  GET  /api/recommend/{user_id}/restaurants
  POST /api/retrain
"""

import sys, os
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add NaviTour path for routing
navitour_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "NaviTour")
sys.path.insert(0, navitour_path)

from fastapi import FastAPI, APIRouter, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import pickle

from dialogue_manager import DialogueManager, get_live_location as get_legacy_live_location

# =========================
# Database
# =========================
def _candidate_database_urls():
    explicit_url = os.getenv("NAVITOUR_DATABASE_URL")
    if explicit_url:
        return [explicit_url]

    db_user = os.getenv("NAVITOUR_DB_USER", "postgres")
    db_password = os.getenv("NAVITOUR_DB_PASSWORD", "528693174")
    db_host = os.getenv("NAVITOUR_DB_HOST", "localhost")
    db_port = os.getenv("NAVITOUR_DB_PORT", "5432")

    explicit_name = os.getenv("NAVITOUR_DB_NAME")
    if explicit_name:
        db_names = [explicit_name]
    else:
        raw_names = os.getenv("NAVITOUR_DB_CANDIDATES", "egypt_transport1,egypt_transport")
        db_names = [name.strip() for name in raw_names.split(",") if name.strip()]

    return [
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        for db_name in db_names
    ]


engine = None
DATABASE_URL = None
_dialogue_sessions = {}
_chat_locations = {}
_route_stop_lookup = None
_route_stop_name_func = None
DEFAULT_CHAT_SESSION = "default"
CHAT_LOCATION_MAX_AGE_SECONDS = int(os.getenv("NAVITOUR_CHAT_LOCATION_MAX_AGE_SECONDS", "180"))


class ChatMessageIn(BaseModel):
    message: str = ""
    session_id: Optional[str] = None


class ChatResetIn(BaseModel):
    session_id: Optional[str] = None


class LiveLocationIn(BaseModel):
    lat: float
    lon: float
    accuracy: Optional[float] = None
    session_id: Optional[str] = None


def _normalize_session_id(session_id: Optional[str]) -> str:
    cleaned = (session_id or "").strip()
    return cleaned or DEFAULT_CHAT_SESSION


def _get_live_location_for_session(session_id: str):
    info = _chat_locations.get(session_id)
    if not info:
        return None

    if time.time() - info["updated_at"] > CHAT_LOCATION_MAX_AGE_SECONDS:
        return None

    return info["lat"], info["lon"]


def _get_dialogue_manager(session_id: Optional[str]):
    sid = _normalize_session_id(session_id)
    manager = _dialogue_sessions.get(sid)
    if manager is None:
        manager = DialogueManager(
            live_location_provider=lambda sid=sid: _get_live_location_for_session(sid) or get_legacy_live_location()
        )
        _dialogue_sessions[sid] = manager
    return manager, sid


def get_engine():
    global engine, DATABASE_URL
    if engine is not None:
        return engine

    last_error = None
    for url in _candidate_database_urls():
        candidate = create_engine(url, pool_pre_ping=True)
        try:
            with candidate.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine = candidate
            DATABASE_URL = url
            print(f"✅ Connected to database: {url.rsplit('/', 1)[-1]}")
            return engine
        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        "Could not connect to any configured NaviTour database. "
        "Set NAVITOUR_DATABASE_URL or NAVITOUR_DB_NAME if needed."
    ) from last_error


def active_database_name():
    if not DATABASE_URL:
        return None
    return DATABASE_URL.rsplit("/", 1)[-1]


def run_migrations():
    """Add password column and fix sequence. Safe to run every time."""
    try:
        db = get_engine()
        with db.begin() as conn:
            conn.execute(text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS password TEXT"))
            seq_exists = conn.execute(text("SELECT to_regclass('users_user_id_seq')")).scalar()
            if seq_exists:
                conn.execute(text("""
                    SELECT setval(
                        'users_user_id_seq',
                        GREATEST(COALESCE((SELECT MAX(user_id) FROM users), 1), 1),
                        true
                    )
                """))
        print("✅ Startup migrations applied")
    except Exception as exc:
        print(f"⚠️ Startup migrations skipped: {exc}")


def _table_exists(table_name: str) -> bool:
    with get_engine().connect() as conn:
        return bool(conn.execute(text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
            LIMIT 1
        """), {"table_name": table_name}).scalar())


def _using_metro_schema() -> bool:
    return _table_exists("metro_stations")


def _get_route_stop_lookup():
    global _route_stop_lookup
    if _route_stop_lookup is None:
        lookup = {}
        if network is not None:
            for stop in network.stops.itertuples():
                lookup[str(stop.stop_id)] = {
                    "lat": float(stop.stop_lat),
                    "lon": float(stop.stop_lon),
                }
        _route_stop_lookup = lookup
    return _route_stop_lookup


def _get_route_stop_name_func():
    global _route_stop_name_func
    if _route_stop_name_func is None and network is not None:
        from raptor.output_translation import load_translations

        _route_stop_name_func = load_translations(
            os.path.join(navitour_path, "data", "translations.txt"),
            network,
        )
    return _route_stop_name_func


def _serialize_route_leg(leg: dict) -> dict:
    stop_lookup = _get_route_stop_lookup()
    stop_name_func = _get_route_stop_name_func()

    raw_stop_ids = leg.get("stops") or []
    if not raw_stop_ids:
        raw_stop_ids = [leg.get("from_stop"), leg.get("to_stop")]

    stop_points = []
    stop_names = []
    for raw_stop_id in raw_stop_ids:
        if raw_stop_id is None:
            continue

        stop_id = str(raw_stop_id)
        stop_name = stop_name_func(stop_id) if stop_name_func else stop_id
        stop_names.append(stop_name)

        coords = stop_lookup.get(stop_id)
        if coords:
            stop_points.append({
                "stop_id": stop_id,
                "name": stop_name,
                "lat": coords["lat"],
                "lon": coords["lon"],
            })

    from_stop_id = str(leg.get("from_stop")) if leg.get("from_stop") is not None else None
    to_stop_id = str(leg.get("to_stop")) if leg.get("to_stop") is not None else None
    from_coords = stop_lookup.get(from_stop_id) if from_stop_id else None
    to_coords = stop_lookup.get(to_stop_id) if to_stop_id else None

    return {
        "mode": leg.get("mode"),
        "agency": leg.get("agency"),
        "route_short": leg.get("route_short"),
        "route_long": leg.get("route_long"),
        "trip_id": leg.get("trip_id"),
        "shape_id": leg.get("shape_id"),
        "from_stop_id": from_stop_id,
        "to_stop_id": to_stop_id,
        "from_stop": stop_name_func(from_stop_id) if stop_name_func and from_stop_id else from_stop_id,
        "to_stop": stop_name_func(to_stop_id) if stop_name_func and to_stop_id else to_stop_id,
        "stops": stop_names,
        "stop_points": stop_points,
        "from_lat": from_coords["lat"] if from_coords else None,
        "from_lon": from_coords["lon"] if from_coords else None,
        "to_lat": to_coords["lat"] if to_coords else None,
        "to_lon": to_coords["lon"] if to_coords else None,
    }


def _serialize_route_option(option: dict, option_index: int = 0, recommended: bool = False) -> dict:
    raw_route = option.get("route")
    if raw_route is None:
        raw_route = option.get("legs") or []

    return {
        "option_index": option_index,
        "recommended": bool(recommended),
        "summary": option.get("summary", {}),
        "route": [_serialize_route_leg(leg) for leg in raw_route],
    }


def _build_serialized_route_payload(
    raw_legs,
    *,
    summary=None,
    start_name=None,
    destination_name=None,
    departure_time=None,
    used_live_location=False,
    route_options=None,
):
    serialized_options = []
    for index, option in enumerate(route_options or []):
        serialized_options.append(
            _serialize_route_option(
                option,
                option_index=index,
                recommended=(index == 0),
            )
        )

    return {
        "legs": [_serialize_route_leg(leg) for leg in (raw_legs or [])],
        "summary": summary or {},
        "start_name": start_name,
        "destination_name": destination_name,
        "departure_time": departure_time or (summary or {}).get("departure_time"),
        "used_live_location": bool(used_live_location),
        "route_options": serialized_options,
        "selected_option_index": 0 if serialized_options else None,
    }

# =========================
# Base router (stations)
# =========================
base = APIRouter(prefix="/api", tags=["stations"])


@base.get("/stations")
def get_all_stations():
    """All Cairo Metro stations with real GPS coordinates."""
    with get_engine().connect() as conn:
        if _using_metro_schema():
            rows = conn.execute(text("""
                SELECT station_id,
                       name_ar AS name,
                       name_en,
                       line,
                       seq,
                       is_interchange,
                       ST_Y(geom::geometry) AS lat,
                       ST_X(geom::geometry) AS lon
                FROM metro_stations
                ORDER BY line, seq
            """)).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT station_id, name, city, type,
                       ST_Y(geometry::geometry) AS lat,
                       ST_X(geometry::geometry) AS lon
                FROM stations ORDER BY name
            """)).mappings().all()
    return [dict(r) for r in rows]


@base.get("/stations/{station_name}/restaurants")
def nearby_restaurants(
    station_name: str,
    distance_m: int = Query(800, description="Radius in metres")
):
    """Restaurants near a station ordered by distance."""
    with get_engine().connect() as conn:
        if _using_metro_schema():
            rows = conn.execute(text("""
                SELECT r.restaurant_id, r.name, r.cuisine,
                       ROUND(ST_Distance(s.geom::geography, r.geom::geography)) AS distance_m,
                       ST_Y(r.geom::geometry) AS lat,
                       ST_X(r.geom::geometry) AS lon
                FROM metro_stations s
                JOIN restaurants r ON ST_DWithin(s.geom::geography, r.geom::geography, :d)
                WHERE (s.name_ar = :st OR s.name_en = :st) AND r.name IS NOT NULL
                ORDER BY distance_m LIMIT 10
            """), {"st": station_name, "d": distance_m}).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT r.restaurant_id, r.name, r.cuisine,
                       ROUND(ST_Distance(s.geometry::geography, r.geom::geography)) AS distance_m,
                       ST_Y(r.geom::geometry) AS lat,
                       ST_X(r.geom::geometry) AS lon
                FROM stations s
                JOIN restaurants r ON ST_DWithin(s.geometry::geography, r.geom::geography, :d)
                WHERE s.name = :st AND r.name IS NOT NULL
                ORDER BY distance_m LIMIT 10
            """), {"st": station_name, "d": distance_m}).mappings().all()
    return {"station": station_name, "radius_m": distance_m,
            "count": len(rows), "restaurants": [dict(r) for r in rows]}


@base.get("/stations/{station_name}/places")
def nearby_places(
    station_name: str,
    distance_m: int = Query(500, description="Radius in metres")
):
    """Tourist places near a station ordered by distance."""
    with get_engine().connect() as conn:
        if _using_metro_schema():
            rows = conn.execute(text("""
                SELECT p.place_id, p.name, p.category,
                       ROUND(ST_Distance(s.geom::geography, p.geom::geography)) AS distance_m,
                       ST_Y(p.geom::geometry) AS lat,
                       ST_X(p.geom::geometry) AS lon
                FROM metro_stations s
                JOIN places p ON ST_DWithin(s.geom::geography, p.geom::geography, :d)
                WHERE (s.name_ar = :st OR s.name_en = :st) AND p.name IS NOT NULL
                ORDER BY distance_m LIMIT 10
            """), {"st": station_name, "d": distance_m}).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT p.place_id, p.name, p.category,
                       ROUND(ST_Distance(s.geometry::geography, p.geom::geography)) AS distance_m,
                       ST_Y(p.geom::geometry) AS lat,
                       ST_X(p.geom::geometry) AS lon
                FROM stations s
                JOIN places p ON ST_DWithin(s.geometry::geography, p.geom::geography, :d)
                WHERE s.name = :st AND p.name IS NOT NULL
                ORDER BY distance_m LIMIT 10
            """), {"st": station_name, "d": distance_m}).mappings().all()
    return {"station": station_name, "radius_m": distance_m,
            "count": len(rows), "places": [dict(r) for r in rows]}


@base.get("/bus-stops")
def get_bus_stops(
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_m: int = Query(1000),
    agency_id: Optional[str] = Query(None),
):
    """Bus stops, optionally filtered by area or agency."""
    if not _table_exists("bus_stops"):
        return []

    filters = []
    params = {}

    if lat is not None and lon is not None:
        filters.append("""
            ST_DWithin(
                b.geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
        """)
        params.update({"lat": lat, "lon": lon, "radius": radius_m})

    if agency_id:
        filters.append("b.agency_id = :agency")
        params["agency"] = agency_id

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    with get_engine().connect() as conn:
        rows = conn.execute(text(f"""
            SELECT b.stop_id, b.name_ar, b.name_en, b.agency_id,
                   b.near_metro, b.near_dist_m,
                   ST_Y(b.geom::geometry) AS lat,
                   ST_X(b.geom::geometry) AS lon,
                   ms.name_ar AS metro_name_ar
            FROM bus_stops b
            LEFT JOIN metro_stations ms ON b.near_metro = ms.station_id
            {where_clause}
            ORDER BY b.stop_id
            LIMIT 200
        """), params).mappings().all()
    return [dict(r) for r in rows]


@base.get("/route")
def get_route(
    start: str = Query(..., description="Starting station name in Arabic"),
    end: str = Query(..., description="Ending station name in Arabic"),
    time: Optional[str] = Query(None, description="Departure time in HH:MM:SS format; defaults to current time")
):
    """Get public transport route between two stations using RAPTOR algorithm."""
    if network is None:
        raise HTTPException(status_code=503, detail="Routing service not available")

    try:
        from raptor.services.raptor_service import run_raptor_plan_from_assistant_json
        departure_time = (time or "").strip() or datetime.now().strftime("%H:%M:%S")

        assistant_json = {
            "intent": "navigation",
            "start_point": {"official_name_ar": start},
            "end_point": {"official_name_ar": end}
        }

        result = run_raptor_plan_from_assistant_json(network, assistant_json, departure_time)

        if isinstance(result, str):
            raise HTTPException(status_code=400, detail=result)
        return {
            "route": [_serialize_route_leg(leg) for leg in result["legs"]],
            "route_options": [
                _serialize_route_option(option, option_index=index, recommended=(index == 0))
                for index, option in enumerate(result.get("route_options", []))
            ],
            "summary": result.get("summary", {}),
            "departure_time": departure_time,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Routing error: {str(e)}")


@base.get("/metro-stations/geojson")
def get_metro_stations_geojson():
    """Get all metro stations as GeoJSON with line colors."""
    if not _table_exists("metro_stations"):
        return {"type": "FeatureCollection", "features": []}

    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT station_id, name_ar, name_en, line, seq,
                   ST_Y(geom::geometry) AS lat,
                   ST_X(geom::geometry) AS lon
            FROM metro_stations
            ORDER BY line, seq
        """)).mappings().all()

    features = []
    for r in rows:
        color = "#e74c3c" if r["line"] == "L1" else "#3498db"  # Red for L1, Blue for L2
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["lon"], r["lat"]]
            },
            "properties": {
                "station_id": r["station_id"],
                "name_ar": r["name_ar"],
                "name_en": r["name_en"],
                "line": r["line"],
                "seq": r["seq"],
                "color": color,
                "type": "metro"
            }
        })

    return {"type": "FeatureCollection", "features": features}


@base.get("/bus-stops/geojson")
def get_bus_stops_geojson():
    """Get all bus stops as GeoJSON with agency colors."""
    if not _table_exists("bus_stops"):
        return {"type": "FeatureCollection", "features": []}

    agency_colors = {
        "P_O_14": "#2ecc71",  # Green
        "CTA": "#f39c12",     # Orange
        "CTA_M": "#9b59b6",   # Purple
        "P_B_8": "#e67e22",   # Dark Orange
        "MM": "#1abc9c",      # Turquoise
        "COOP": "#34495e",    # Dark Gray
        "GRN": "#16a085",     # Green Sea
        "BOX": "#8e44ad",     # Wisteria
        "LTRA_M": "#c0392b"   # Dark Red
    }

    with get_engine().connect() as conn:
        rows = conn.execute(text("""
            SELECT stop_id, name_ar, name_en, agency_id, near_metro, near_dist_m,
                   ST_Y(geom::geometry) AS lat,
                   ST_X(geom::geometry) AS lon
            FROM bus_stops
            ORDER BY stop_id
        """)).mappings().all()

    features = []
    for r in rows:
        color = agency_colors.get(r["agency_id"], "#95a5a6")  # Gray default
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["lon"], r["lat"]]
            },
            "properties": {
                "stop_id": r["stop_id"],
                "name_ar": r["name_ar"],
                "name_en": r["name_en"],
                "agency_id": r["agency_id"],
                "near_metro": r["near_metro"],
                "near_dist_m": r["near_dist_m"],
                "color": color,
                "type": "bus"
            }
        })

    return {"type": "FeatureCollection", "features": features}


@base.get("/bus-stops/{stop_id}/recommendations")
def get_bus_stop_recommendations(
    stop_id: int,
    user_id: str = Query("1", description="User ID for personalization"),
    radius_m: int = Query(1000),
):
    """Get restaurant & place recommendations near a bus stop."""
    if not _table_exists("bus_stops"):
        raise HTTPException(status_code=404, detail="bus_stops table not found")

    with get_engine().connect() as conn:
        # Get bus stop location
        stop = conn.execute(text("""
            SELECT name_ar, name_en, geom FROM bus_stops WHERE stop_id = :id
        """), {"id": stop_id}).mappings().first()

        if not stop:
            raise HTTPException(status_code=404, detail=f"Bus stop {stop_id} not found")

        # Get recommendations
        recs = conn.execute(text("""
            SELECT r.name, r.cuisine, ROUND(ST_Distance(b.geom::geography, r.geom::geography)) AS distance_m
            FROM bus_stops b
            JOIN restaurants r ON ST_DWithin(b.geom::geography, r.geom::geography, :radius)
            WHERE b.stop_id = :stop_id
            ORDER BY distance_m LIMIT 15
        """), {"stop_id": stop_id, "radius": radius_m}).mappings().all()

        return {
            "stop_id": stop_id,
            "stop_name": stop["name_ar"],
            "radius_m": radius_m,
            "count": len(recs),
            "recommendations": [dict(r) for r in recs]
        }


# =========================
# Load RAPTOR Network
# =========================
try:
    network_path = os.path.join(navitour_path, "data", "network.pkl")
    with open(network_path, "rb") as f:
        network = pickle.load(f)
    print("✅ RAPTOR network loaded successfully")
except Exception as e:
    print(f"❌ Failed to load RAPTOR network: {e}")
    network = None

# =========================
# App
# =========================
app = FastAPI(
    title="NaviTour — Egypt Transport Recommendation API",
    description="""
## Hybrid Recommendation Engine for Cairo Metro

### Main endpoint
`GET /api/recommend/{user_id}` — personalized hybrid recommendations

**By GPS:**
```
/api/recommend/1?lat=30.0444&lon=31.2357&radius_m=1000
```
**By Station:**
```
/api/recommend/1?station=السادات&radius_m=1000
```

### Scoring (4 signals)
| Signal | Weight | Description |
|---|---|---|
| Proximity | 30% | Closer items score higher |
| SVD | 30% | Collaborative filtering prediction |
| Popularity | 20% | avg_rating × log(num_ratings) |
| Category match | 20% | User's historical preferences |
    """,
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    run_migrations()


@app.get("/health", tags=["system"])
def health_check():
    """API and database health + row counts."""
    try:
        with get_engine().connect() as conn:
            if _using_metro_schema():
                counts = conn.execute(text("""
                    SELECT
                        (SELECT COUNT(*) FROM metro_stations) AS metro_stations,
                        (SELECT COUNT(*) FROM bus_stops)      AS bus_stops,
                        (SELECT COUNT(*) FROM places)         AS places,
                        (SELECT COUNT(*) FROM restaurants)    AS restaurants,
                        (SELECT COUNT(*) FROM users)          AS users,
                        (SELECT COUNT(*) FROM ratings)        AS ratings
                """)).mappings().one()
            else:
                counts = conn.execute(text("""
                    SELECT
                        (SELECT COUNT(*) FROM stations)    AS stations,
                        (SELECT COUNT(*) FROM places)      AS places,
                        (SELECT COUNT(*) FROM restaurants) AS restaurants,
                        (SELECT COUNT(*) FROM users)       AS users,
                        (SELECT COUNT(*) FROM ratings)     AS ratings
                """)).mappings().one()
        return {
            "status": "ok",
            "database": "connected",
            "database_name": active_database_name(),
            **dict(counts),
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# Register base router (stations)
app.include_router(base)

# Register recommendation router
from recommender.router import router as rec_router, init_router
init_router(get_engine)
app.include_router(rec_router)


@app.post("/message", tags=["chat"])
def chat_message(payload: ChatMessageIn):
    manager, session_id = _get_dialogue_manager(payload.session_id)
    reply = manager.process(payload.message)
    route_payload = None
    if manager.last_legs:
        route_payload = _build_serialized_route_payload(
            manager.last_legs,
            summary=manager.last_route_summary,
            start_name=(manager.last_route_context or {}).get("start_name"),
            destination_name=(manager.last_route_context or {}).get("destination_name"),
            departure_time=(manager.last_route_context or {}).get("departure_time"),
            used_live_location=(manager.last_route_context or {}).get("used_live_location"),
            route_options=manager.last_route_options,
        )

    live_location = _get_live_location_for_session(session_id)
    return {
        "reply": reply,
        "session_id": session_id,
        "has_route": bool(manager.last_legs),
        "route": route_payload,
        "live_location": (
            {"lat": live_location[0], "lon": live_location[1]}
            if live_location else None
        ),
    }


@app.post("/reset", tags=["chat"])
def chat_reset(payload: Optional[ChatResetIn] = Body(default=None)):
    requested_session_id = payload.session_id if payload else None
    manager, session_id = _get_dialogue_manager(requested_session_id)
    manager.reset_conversation()
    return {"status": "ok", "session_id": session_id}


@app.post("/api/location", tags=["chat"])
def update_live_location(payload: LiveLocationIn):
    session_id = _normalize_session_id(payload.session_id)
    _chat_locations[session_id] = {
        "lat": float(payload.lat),
        "lon": float(payload.lon),
        "accuracy": float(payload.accuracy) if payload.accuracy is not None else None,
        "updated_at": time.time(),
    }
    return {"status": "ok", "session_id": session_id}


# =========================
# User Login / Register (with password)
# =========================

@app.post("/api/users/register", tags=["users"])
def register_or_login(
    name: str = Body(...),
    password: str = Body(...)
):
    import hashlib, os

    def _hash(pw, salt=None):
        if salt is None:
            salt = os.urandom(16).hex()
        return salt + ":" + hashlib.sha256((salt + pw).encode()).hexdigest()

    def _verify(pw, stored):
        try:
            salt = stored.split(":")[0]
            return _hash(pw, salt) == stored
        except Exception:
            return False

    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    if not password:
        raise HTTPException(status_code=400, detail="Password cannot be empty")

    try:
        with get_engine().connect() as conn:
            existing = conn.execute(
                text("SELECT user_id, name, password FROM users WHERE LOWER(name) = LOWER(:name)"),
                {"name": name}
            ).mappings().first()

        if existing:
            uid    = existing["user_id"]
            stored = existing["password"]
            if stored:
                if not _verify(password, stored):
                    raise HTTPException(status_code=401, detail="Wrong password. Try again.")
            else:
                # No password yet — set it now
                with get_engine().begin() as conn:
                    conn.execute(text("UPDATE users SET password=:pw WHERE user_id=:uid"),
                                 {"pw": _hash(password), "uid": uid})
            return {
                "status":  "ok",
                "user_id": existing["user_id"],
                "name":    existing["name"],
                "is_new":  False,
                "message": f"Welcome back, {existing['name']}!"
            }

        # New user
        with get_engine().begin() as conn:
            result = conn.execute(
                text("INSERT INTO users (name, password) VALUES (:name, :pw) RETURNING user_id"),
                {"name": name, "pw": _hash(password)}
            )
            new_id = result.fetchone()[0]
        return {
            "status":  "ok",
            "user_id": new_id,
            "name":    name,
            "is_new":  True,
            "message": f"Welcome, {name}!"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/users/{user_id}", tags=["users"])
def get_user(user_id: int):
    """Get user info by ID (password not returned)."""
    with get_engine().connect() as conn:
        user = conn.execute(
            text("SELECT user_id, name FROM users WHERE user_id = :uid"),
            {"uid": user_id}
        ).mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return dict(user)


# =========================
# User Preferences (seed ratings from onboarding)
# =========================

@app.post("/api/users/{user_id}/preferences", tags=["users"])
def save_preferences(
    user_id: int,
    cuisines: list = Body(default=[]),
    place_cats: list = Body(default=[]),
    radius: int = Body(default=1000)
):
    """
    Save onboarding preferences for a new user as seed ratings.
    Inserts rating=4 for one matching item per selected category.
    Safe to call multiple times — skipped if user already has real ratings.
    """
    with get_engine().connect() as conn:
        existing_count = conn.execute(
            text("SELECT COUNT(*) FROM ratings WHERE user_id = :uid"),
            {"uid": user_id}
        ).scalar()

    if existing_count > 0:
        return {"status": "skipped", "message": "User already has ratings"}

    seed_rows = []
    with get_engine().connect() as conn:
        # Fetch up to 3 restaurants per selected cuisine for stronger signal
        for cuisine in cuisines:
            rows = conn.execute(
                text("SELECT restaurant_id FROM restaurants WHERE LOWER(cuisine) LIKE LOWER(:c) LIMIT 3"),
                {"c": f"%{cuisine}%"}
            ).fetchall()
            for row in rows:
                seed_rows.append(("restaurant", row[0]))

        # Fetch up to 3 places per selected category
        for cat in place_cats:
            rows = conn.execute(
                text("SELECT place_id FROM places WHERE LOWER(category) LIKE LOWER(:c) LIMIT 3"),
                {"c": f"%{cat}%"}
            ).fetchall()
            for row in rows:
                seed_rows.append(("place", row[0]))

    if not seed_rows:
        return {"status": "ok", "seeded": 0, "message": "No matching items found for preferences"}

    inserted = 0
    with get_engine().begin() as conn:
        for place_type, item_id in seed_rows:
            exists = conn.execute(
                text("SELECT 1 FROM ratings WHERE user_id=:uid AND place_type=:pt AND place_id=:iid"),
                {"uid": user_id, "pt": place_type, "iid": item_id}
            ).first()
            if not exists:
                # Use rating=5 so category_preferences() registers strong affinity above global avg
                conn.execute(
                    text("INSERT INTO ratings (user_id, place_type, place_id, rating, review) VALUES (:uid, :pt, :iid, 5, 'Onboarding preference')"),
                    {"uid": user_id, "pt": place_type, "iid": item_id}
                )
                inserted += 1

    return {"status": "ok", "seeded": inserted, "message": f"Saved {inserted} preference seeds — recommendations personalized!"}


# =========================
# RATINGS — Submit / Update / View
# DB column name is 'place_id' (not 'item_id')
# =========================

class RatingIn(BaseModel):
    user_id: int
    place_type: str        # "place" or "restaurant"
    item_id: int           # place_id or restaurant_id
    rating: int            # 1-5 stars
    review: Optional[str] = ""

@app.post("/api/ratings", tags=["ratings"])
def submit_rating(payload: RatingIn):
    user_id    = payload.user_id
    place_type = payload.place_type
    item_id    = payload.item_id
    rating     = payload.rating
    review     = payload.review or ""

    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    if place_type not in ["place", "restaurant"]:
        raise HTTPException(status_code=400, detail="place_type must be 'place' or 'restaurant'")

    try:
        with get_engine().begin() as conn:
            # Verify user exists
            user = conn.execute(
                text("SELECT user_id FROM users WHERE user_id = :uid"),
                {"uid": user_id}
            ).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"User {user_id} not found")

            # Verify item exists
            if place_type == "place":
                item = conn.execute(
                    text("SELECT place_id FROM places WHERE place_id = :iid"),
                    {"iid": item_id}
                ).first()
                if not item:
                    raise HTTPException(status_code=404, detail=f"Place {item_id} not found")
            else:
                item = conn.execute(
                    text("SELECT restaurant_id FROM restaurants WHERE restaurant_id = :iid"),
                    {"iid": item_id}
                ).first()
                if not item:
                    raise HTTPException(status_code=404, detail=f"Restaurant {item_id} not found")

            # Check if user already rated this item
            existing = conn.execute(
                text("""
                    SELECT rating_id FROM ratings
                    WHERE user_id = :uid AND place_type = :pt AND place_id = :iid
                """),
                {"uid": user_id, "pt": place_type, "iid": item_id}
            ).first()

            if existing:
                # UPDATE existing rating
                conn.execute(
                    text("""
                        UPDATE ratings
                        SET rating = :r, review = :rev, created_at = NOW()
                        WHERE user_id = :uid AND place_type = :pt AND place_id = :iid
                    """),
                    {"uid": user_id, "pt": place_type, "iid": item_id, "r": rating, "rev": review}
                )
                return {
                    "status": "ok",
                    "action": "updated",
                    "message": "Rating updated successfully!",
                    "user_id": user_id,
                    "item_id": item_id,
                    "rating": rating,
                    "review": review
                }
            else:
                # INSERT new rating (DB column is 'place_id')
                result = conn.execute(
                    text("""
                        INSERT INTO ratings (user_id, place_type, place_id, rating, review)
                        VALUES (:uid, :pt, :iid, :r, :rev)
                        RETURNING rating_id
                    """),
                    {"uid": user_id, "pt": place_type, "iid": item_id, "r": rating, "rev": review}
                )
                rating_id = result.fetchone()[0]
                return {
                    "status": "ok",
                    "action": "created",
                    "rating_id": rating_id,
                    "message": "Rating submitted successfully!",
                    "user_id": user_id,
                    "item_id": item_id,
                    "rating": rating,
                    "review": review
                }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/ratings/{user_id}", tags=["ratings"])
def get_user_ratings(user_id: int):
    """Get all ratings submitted by a user."""
    with get_engine().connect() as conn:
        user = conn.execute(
            text("SELECT user_id FROM users WHERE user_id = :uid"),
            {"uid": user_id}
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")

        # NOTE: DB column is 'place_id' — aliased to 'item_id' in response
        ratings = conn.execute(
            text("""
                SELECT rating_id, user_id, place_type,
                       place_id AS item_id,
                       rating, review, created_at
                FROM ratings
                WHERE user_id = :uid
                ORDER BY created_at DESC
            """),
            {"uid": user_id}
        ).mappings().all()

    return {
        "user_id": user_id,
        "total_ratings": len(ratings),
        "ratings": [dict(r) for r in ratings]
    }


@app.get("/api/item-ratings", tags=["ratings"])
def get_item_ratings(
    place_type: str,  # "place" or "restaurant"
    item_id: int      # place_id or restaurant_id
):
    """Get all ratings for a specific place or restaurant."""
    if place_type not in ["place", "restaurant"]:
        raise HTTPException(status_code=400, detail="place_type must be 'place' or 'restaurant'")

    with get_engine().connect() as conn:
        # NOTE: DB column is 'place_id' (not 'item_id')
        ratings = conn.execute(
            text("""
                SELECT rating_id, user_id, rating, review, created_at
                FROM ratings
                WHERE place_type = :pt AND place_id = :iid
                ORDER BY created_at DESC
            """),
            {"pt": place_type, "iid": item_id}
        ).mappings().all()

    avg_rating = round(sum(r["rating"] for r in ratings) / len(ratings), 2) if ratings else 0

    return {
        "place_type": place_type,
        "item_id": item_id,
        "total_ratings": len(ratings),
        "average_rating": avg_rating,
        "ratings": [dict(r) for r in ratings]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
