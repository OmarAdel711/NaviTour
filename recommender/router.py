"""
Recommendation Router
─────────────────────
Exposes the hybrid recommendation engine via FastAPI.

Endpoints:
  GET /api/recommend/{user_id}
      ?lat=&lon=&radius_m=&top_n=        ← by GPS coordinates
      ?station=&radius_m=&top_n=         ← by station name

Response includes merged places + restaurants,
ranked by hybrid score with full score breakdown.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from sqlalchemy import text

router = APIRouter(prefix="/api", tags=["recommendations"])

# engine getter injected from app.py
_get_engine = None

def init_router(engine):
    global _get_engine
    _get_engine = engine


def engine():
    if _get_engine is None:
        raise RuntimeError("Recommendation router is not initialized with a database engine")
    return _get_engine()


def _table_has_column(db, table_name: str, column_name: str) -> bool:
    with db.connect() as conn:
        return bool(conn.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
        """), {"table_name": table_name, "column_name": column_name}).scalar())


# ═══════════════════════════════════════════════════════════════
# GET /api/recommend/{user_id}
# ═══════════════════════════════════════════════════════════════

@router.get("/recommend/{user_id}")
def recommend(
    user_id:   int,
    lat:       Optional[float] = Query(None,  description="User latitude (GPS mode)"),
    lon:       Optional[float] = Query(None,  description="User longitude (GPS mode)"),
    station:   Optional[str]   = Query(None,  description="Station name (station mode)"),
    radius_m:  int             = Query(1000,  description="Search radius in metres"),
    top_n:     int             = Query(10,    description="Max results to return"),
):
    """
    Hybrid recommendation endpoint.

    Provide EITHER (lat + lon) OR station name — not both.

    Scoring formula:
      proximity     30%  — exponential decay by distance
      svd           30%  — collaborative filtering (SVD)
      popularity    20%  — avg_rating × log(num_ratings+1)
      category_pref 20%  — user's historical tag preferences
    """
    from recommender.scoring import (
        fetch_candidates,
        fetch_candidates_by_station,
        score_candidates,
    )

    # ── Validate user exists ──────────────────────────────────
    db = engine()

    with db.connect() as conn:
        user = conn.execute(
            text("SELECT user_id, name FROM users WHERE user_id = :uid"),
            {"uid": user_id}
        ).mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    # ── Resolve origin ────────────────────────────────────────
    origin_label = None

    if lat is not None and lon is not None and station:
        raise HTTPException(
            status_code=422,
            detail="Provide either (lat + lon) or station, not both"
        )

    if lat is not None and lon is not None:
        # GPS mode
        candidates    = fetch_candidates(db, lat, lon, radius_m)
        origin_label  = f"GPS ({lat:.5f}, {lon:.5f})"
        origin_lat, origin_lon = lat, lon

    elif station:
        # Station mode
        candidates, origin_lat, origin_lon = fetch_candidates_by_station(
            db, station, radius_m
        )
        if origin_lat is None:
            raise HTTPException(status_code=404, detail=f"Station '{station}' not found")
        origin_label = f"Station: {station}"

    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either (lat + lon) for GPS mode, or station= for station mode"
        )

    if not candidates:
        return {
            "user_id":       user_id,
            "user_name":     user["name"],
            "origin":        origin_label,
            "radius_m":      radius_m,
            "total_found":   0,
            "recommendations": []
        }

    # ── Score & rank ──────────────────────────────────────────
    ranked = score_candidates(db, user_id, candidates)
    top    = ranked[:top_n]

    # ── Format response ───────────────────────────────────────
    return {
        "user_id":     user_id,
        "user_name":   user["name"],
        "origin":      origin_label,
        "origin_lat":  origin_lat,
        "origin_lon":  origin_lon,
        "radius_m":    radius_m,
        "total_found": len(ranked),
        "showing":     len(top),
        "recommendations": [
            {
                "rank":       i + 1,
                "item_id":    r["id"],              # DB primary key (place_id or restaurant_id)
                "type":       r["type"],           # "place" or "restaurant"
                "name":       r["name"],
                "tag":        r["tag"],             # category or cuisine
                "distance_m": r["distance_m"],
                "lat":        r["lat"],
                "lon":        r["lon"],
                "score":      r["score"],           # 0–1, higher = better
                "score_breakdown": r["score_breakdown"],
            }
            for i, r in enumerate(top)
        ]
    }


# ═══════════════════════════════════════════════════════════════
# GET /api/recommend/{user_id}/places   (places only)
# GET /api/recommend/{user_id}/restaurants  (restaurants only)
# ═══════════════════════════════════════════════════════════════

@router.get("/recommend/{user_id}/places")
def recommend_places(
    user_id:  int,
    lat:      Optional[float] = Query(None),
    lon:      Optional[float] = Query(None),
    station:  Optional[str]   = Query(None),
    radius_m: int             = Query(1000),
    top_n:    int             = Query(10),
):
    """Same as /recommend but filters to places only."""
    result = recommend(user_id, lat, lon, station, radius_m, top_n * 3)
    result["recommendations"] = [
        r for r in result["recommendations"] if r["type"] == "place"
    ][:top_n]
    result["showing"] = len(result["recommendations"])
    return result


@router.get("/recommend/{user_id}/restaurants")
def recommend_restaurants(
    user_id:  int,
    lat:      Optional[float] = Query(None),
    lon:      Optional[float] = Query(None),
    station:  Optional[str]   = Query(None),
    radius_m: int             = Query(1000),
    top_n:    int             = Query(10),
):
    """Same as /recommend but filters to restaurants only."""
    result = recommend(user_id, lat, lon, station, radius_m, top_n * 3)
    result["recommendations"] = [
        r for r in result["recommendations"] if r["type"] == "restaurant"
    ][:top_n]
    result["showing"] = len(result["recommendations"])
    return result


# ═══════════════════════════════════════════════════════════════
# POST /api/retrain   (force SVD retrain after new ratings)
# ═══════════════════════════════════════════════════════════════

@router.post("/retrain")
def retrain_model():
    """Force the SVD model to retrain on latest ratings data."""
    from recommender.svd_model import retrain
    retrain(engine())
    return {"status": "ok", "message": "SVD model retrained successfully"}


# ═══════════════════════════════════════════════════════════════
# GET /api/recommend/{user_id}/along-route
# ═══════════════════════════════════════════════════════════════

@router.get("/recommend/{user_id}/along-route")
def recommend_along_route(
    user_id: int,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    radius_m: int = Query(1000, description="Search radius in metres")
):
    """
    Get recommendations along a route from start point to end point.
    
    Returns all places/restaurants near START or END point,
    sorted by distance from START point.
    """
    from math import radians, cos, sin, atan2, sqrt
    db = engine()

    # Calculate distance between two points (haversine formula)
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # Earth radius in meters
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    try:
        with db.connect() as conn:
            user = conn.execute(
                text("SELECT user_id FROM users WHERE user_id = :uid"),
                {"uid": user_id}
            ).first()
            if not user:
                raise HTTPException(status_code=404, detail=f"User {user_id} not found")

            has_place_brief = _table_has_column(db, "places", "brief")
            has_restaurant_brief = _table_has_column(db, "restaurants", "brief")
            place_brief_sql = "p.brief" if has_place_brief else "NULL::text AS brief"
            restaurant_brief_sql = "r.brief" if has_restaurant_brief else "NULL::text AS brief"

            # Get all places/restaurants near START or END point
            results = conn.execute(text(f"""
                SELECT 'place' as type, p.place_id as item_id, p.name, p.category as tag, {place_brief_sql},
                       ST_Y(p.geom::geometry) as lat, ST_X(p.geom::geometry) as lon
                FROM places p
                WHERE ST_DWithin(
                    p.geom::geography,
                    ST_SetSRID(ST_MakePoint(:start_lon, :start_lat), 4326)::geography,
                    :radius
                )
                   OR ST_DWithin(
                    p.geom::geography,
                    ST_SetSRID(ST_MakePoint(:end_lon, :end_lat), 4326)::geography,
                    :radius
                )
                
                UNION ALL
                
                SELECT 'restaurant' as type, r.restaurant_id as item_id, r.name, r.cuisine as tag, {restaurant_brief_sql},
                       ST_Y(r.geom::geometry) as lat, ST_X(r.geom::geometry) as lon
                FROM restaurants r
                WHERE ST_DWithin(
                    r.geom::geography,
                    ST_SetSRID(ST_MakePoint(:start_lon, :start_lat), 4326)::geography,
                    :radius
                )
                   OR ST_DWithin(
                    r.geom::geography,
                    ST_SetSRID(ST_MakePoint(:end_lon, :end_lat), 4326)::geography,
                    :radius
                )
            """), {
                "start_lat": start_lat,
                "start_lon": start_lon,
                "end_lat": end_lat,
                "end_lon": end_lon,
                "radius": radius_m
            }).mappings().all()
        
        # Calculate distance from start point and sort
        recommendations = []
        for item in results:
            dist_from_start = haversine(start_lat, start_lon, float(item["lat"]), float(item["lon"]))
            recommendations.append({
                "type": item["type"],
                "name": item["name"],
                "tag": item["tag"],
                "brief": item["brief"],
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "distance_from_start_m": int(dist_from_start)
            })
        
        # Sort by distance from start
        recommendations.sort(key=lambda x: x["distance_from_start_m"])
        
        # Calculate total route distance
        total_distance = haversine(start_lat, start_lon, end_lat, end_lon)
        
        return {
            "status": "ok",
            "start": {"lat": start_lat, "lon": start_lon},
            "end": {"lat": end_lat, "lon": end_lon},
            "total_distance_m": int(total_distance),
            "search_radius_m": radius_m,
            "recommendations_found": len(recommendations),
            "recommendations": recommendations[:20]  # Top 20
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting route: {str(e)}")
