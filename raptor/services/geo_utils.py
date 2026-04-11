# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 14:18:26 2026

@author: Samia
"""

# raptor/services/geo_utils.py

import requests
from math import radians, cos, sin, sqrt, atan2


def get_lat_lon_from_api(place_name: str):
    """
    Use OpenStreetMap Nominatim API
    to convert Arabic place name → (lat, lon)
    """

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": f"{place_name}, Cairo, Egypt",
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "cairo-transport-assistant"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code != 200:
        return None

    data = response.json()

    if not data:
        return None

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])

    return lat, lon

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two points in KM
    """
    R = 6371  # Earth radius in km

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c

def find_nearest_stop(network, coords, max_distance_km=1.5):
    """
    Find the nearest stop to given coordinates (lat, lon).
    network.stops is assumed to be a DataFrame with 'stop_lat' and 'stop_lon'.
    """
    lat, lon = coords
    min_distance = float("inf")
    nearest_stop_id = None

    for _, stop in network.stops.iterrows():  # iterrows() for DataFrame
        stop_lat = stop["stop_lat"]
        stop_lon = stop["stop_lon"]
        dist = haversine(lat, lon, stop_lat, stop_lon)
        if dist < min_distance:
            min_distance = dist
            nearest_stop_id = stop['stop_id']

    if min_distance > max_distance_km:
        return None

    return nearest_stop_id