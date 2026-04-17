import os
import time

import requests


LOCATION_SERVICE_URL = os.getenv(
    "NAVITOUR_LOCATION_SERVICE_URL",
    "http://127.0.0.1:5000/get_location",
)
DEFAULT_SESSION_ID = "default"
LOCATION_MAX_AGE_SECONDS = int(os.getenv("NAVITOUR_CHAT_LOCATION_MAX_AGE_SECONDS", "180"))

_tracked_locations = {}


def normalize_session_id(session_id):
    cleaned = (session_id or "").strip()
    return cleaned or DEFAULT_SESSION_ID


def fetch_live_location():
    try:
        response = requests.get(LOCATION_SERVICE_URL, timeout=3)
        data = response.json()
        if data["lat"] is None:
            return None
        return float(data["lat"]), float(data["lon"])
    except Exception:
        return None


def get_tracked_location_record(session_id):
    info = _tracked_locations.get(normalize_session_id(session_id))
    if not info:
        return None

    if time.time() - info["updated_at"] > LOCATION_MAX_AGE_SECONDS:
        return None

    return info


def get_tracked_live_location(session_id):
    info = get_tracked_location_record(session_id)
    if not info:
        return None
    return info["lat"], info["lon"]


def get_effective_live_location(session_id=None, allow_fallback=True):
    tracked = get_tracked_live_location(session_id)
    if tracked is not None:
        return tracked

    if allow_fallback:
        return fetch_live_location()

    return None


def get_live_location_payload(session_id=None, allow_fallback=False):
    location = get_effective_live_location(session_id, allow_fallback=allow_fallback)
    if location is None:
        return None

    lat, lon = location
    info = get_tracked_location_record(session_id)
    return {
        "lat": lat,
        "lon": lon,
        "accuracy": info["accuracy"] if info else None,
        "source": "tracked" if info else "fallback",
    }


def update_tracked_live_location(session_id, lat, lon, accuracy=None):
    sid = normalize_session_id(session_id)
    _tracked_locations[sid] = {
        "lat": float(lat),
        "lon": float(lon),
        "accuracy": float(accuracy) if accuracy is not None else None,
        "updated_at": time.time(),
    }
    return sid


def clear_tracked_live_location(session_id):
    _tracked_locations.pop(normalize_session_id(session_id), None)
