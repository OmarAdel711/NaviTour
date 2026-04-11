"""
Hybrid Scoring Engine
─────────────────────
Combines 4 signals into a final recommendation score:

  Signal            Weight   Description
  ─────────────────────────────────────────────────────
  proximity          30%     Closer to user/station → higher
  svd_predicted      30%     SVD predicted personal rating
  popularity         20%     avg_rating × log(num_ratings+1)
  category_pref      20%     User's affinity for this category/cuisine

Final score is in [0, 1]. Higher = better recommendation.
"""

from math import log, exp
from sqlalchemy import text


# ── Weights (must sum to 1.0) ─────────────────────────────────
W_PROXIMITY  = 0.30
W_SVD        = 0.30
W_POPULARITY = 0.20
W_CATEGORY   = 0.20


# ═══════════════════════════════════════════════════════════════
# 1. CANDIDATE FETCH
# ═══════════════════════════════════════════════════════════════

def fetch_candidates(engine, lat: float, lon: float, radius_m: int):
    """
    Fetch all places and restaurants within radius_m of (lat, lon).
    Returns list of dicts with spatial + metadata fields.
    """
    query = text("""
        SELECT
            'place'              AS place_type,
            p.place_id           AS item_id,
            p.name,
            p.category           AS tag,
            ST_Y(p.geom::geometry) AS lat,
            ST_X(p.geom::geometry) AS lon,
            ROUND(ST_Distance(
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                p.geom::geography
            )) AS distance_m
        FROM places p
        WHERE ST_DWithin(
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            p.geom::geography,
            :radius
        )

        UNION ALL

        SELECT
            'restaurant'         AS place_type,
            r.restaurant_id      AS item_id,
            r.name,
            r.cuisine            AS tag,
            ST_Y(r.geom::geometry) AS lat,
            ST_X(r.geom::geometry) AS lon,
            ROUND(ST_Distance(
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                r.geom::geography
            )) AS distance_m
        FROM restaurants r
        WHERE ST_DWithin(
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            r.geom::geography,
            :radius
        )
        ORDER BY distance_m
    """)

    with engine.connect() as conn:
        rows = conn.execute(query, {"lat": lat, "lon": lon, "radius": radius_m}).mappings().all()
    return [dict(r) for r in rows]


def fetch_candidates_by_station(engine, station_name: str, radius_m: int):
    """
    Same as fetch_candidates but using a station as the origin.
    Extracts lat/lon from the stations table then delegates.
    """
    with engine.connect() as conn:
        has_metro_stations = bool(conn.execute(text("""
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'metro_stations'
            LIMIT 1
        """)).scalar())

        if has_metro_stations:
            row = conn.execute(text("""
                SELECT
                    ST_Y(geom::geometry) AS lat,
                    ST_X(geom::geometry) AS lon
                FROM metro_stations
                WHERE name_ar = :name OR name_en = :name
                LIMIT 1
            """), {"name": station_name}).mappings().first()
        else:
            row = conn.execute(text("""
                SELECT
                    ST_Y(geometry::geometry) AS lat,
                    ST_X(geometry::geometry) AS lon
                FROM stations
                WHERE name = :name
                LIMIT 1
            """), {"name": station_name}).mappings().first()

    if not row:
        return [], None, None

    lat, lon = float(row["lat"]), float(row["lon"])
    candidates = fetch_candidates(engine, lat, lon, radius_m)
    return candidates, lat, lon


# ═══════════════════════════════════════════════════════════════
# 2. SIGNAL COMPUTATION
# ═══════════════════════════════════════════════════════════════

def proximity_score(distance_m: float, max_distance_m: float) -> float:
    """
    Exponential decay: items right next to user score ~1.0,
    items at the edge of the radius score ~0.05.
    """
    if max_distance_m <= 0:
        return 1.0
    # Decay constant so that score at max_dist ≈ 0.05
    k = -log(0.05) / max_distance_m
    return round(exp(-k * distance_m), 4)


def popularity_scores(engine) -> dict:
    """
    Compute popularity score for every (place_type, item_id).
    popularity = avg_rating * log(num_ratings + 1)  → normalized to [0,1]
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT place_type,
                   place_id       AS item_id,
                   AVG(rating)    AS avg_rating,
                   COUNT(*)       AS num_ratings
            FROM ratings
            GROUP BY place_type, place_id
        """)).mappings().all()

    raw = {}
    for r in rows:
        key = (r["place_type"], int(r["item_id"]))
        raw_score = float(r["avg_rating"]) * log(int(r["num_ratings"]) + 1)
        raw[key] = raw_score

    if not raw:
        return {}

    max_raw = max(raw.values())
    return {k: round(v / max_raw, 4) for k, v in raw.items()}


def category_preferences(engine, user_id: int) -> dict:
    """
    Compute user's affinity for each category/cuisine tag.
    Returns dict {tag: score_0_to_1}

    Method: for each tag, calculate user's avg rating on items of that tag,
    normalized by global avg. Tags the user rates above global avg → higher score.
    """
    with engine.connect() as conn:
        # User ratings joined with place/restaurant metadata
        rows = conn.execute(text("""
            SELECT
                r.rating,
                COALESCE(p.category, rest.cuisine) AS tag
            FROM ratings r
            LEFT JOIN places      p    ON r.place_type = 'place'      AND r.place_id = p.place_id
            LEFT JOIN restaurants rest ON r.place_type = 'restaurant' AND r.place_id = rest.restaurant_id
            WHERE r.user_id = :uid
              AND COALESCE(p.category, rest.cuisine) IS NOT NULL
        """), {"uid": user_id}).mappings().all()

    if not rows:
        return {}

    from collections import defaultdict
    tag_ratings = defaultdict(list)
    for r in rows:
        # A tag can be composite like "kebab;grill" — split and credit both
        for tag in str(r["tag"]).split(";"):
            tag_ratings[tag.strip()].append(int(r["rating"]))

    global_avg = sum(
        v for vals in tag_ratings.values() for v in vals
    ) / sum(len(vals) for vals in tag_ratings.values())

    prefs = {}
    for tag, ratings_list in tag_ratings.items():
        tag_avg = sum(ratings_list) / len(ratings_list)
        # Normalize: global_avg maps to 0.5, max (5.0) maps to 1.0, min (1.0) maps to 0.0
        prefs[tag] = round((tag_avg - 1) / 4, 4)

    return prefs


# ═══════════════════════════════════════════════════════════════
# 3. HYBRID SCORING
# ═══════════════════════════════════════════════════════════════

def hybrid_score(
    prox:  float,
    svd:   float,
    pop:   float,
    cat:   float,
) -> float:
    """Weighted combination of the 4 signals."""
    return round(
        W_PROXIMITY  * prox +
        W_SVD        * svd  +
        W_POPULARITY * pop  +
        W_CATEGORY   * cat,
        4
    )


def score_candidates(engine, user_id: int, candidates: list) -> list:
    """
    Score all candidates and return sorted list with score breakdown.
    """
    from recommender.svd_model import predict as svd_predict

    if not candidates:
        return []

    max_dist = max(c["distance_m"] for c in candidates) or 1

    # Pre-compute shared signals
    pop_map  = popularity_scores(engine)
    cat_pref = category_preferences(engine, user_id)

    results = []
    for c in candidates:
        place_type = c["place_type"]
        item_id    = int(c["item_id"])
        dist       = float(c["distance_m"])
        tag        = str(c["tag"] or "")

        # ── Signal 1: Proximity ───────────────────────────────
        s_prox = proximity_score(dist, max_dist)

        # ── Signal 2: SVD predicted rating → normalize to [0,1] ──
        svd_raw  = svd_predict(engine, user_id, place_type, item_id)
        s_svd    = round((svd_raw - 1) / 4, 4)

        # ── Signal 3: Popularity ──────────────────────────────
        s_pop = pop_map.get((place_type, item_id), 0.3)  # default 0.3

        # ── Signal 4: Category preference ────────────────────
        # Average affinity across all tags (handles "kebab;grill")
        tags = [t.strip() for t in tag.split(";") if t.strip()]
        if tags:
            s_cat = round(sum(cat_pref.get(t, 0.3) for t in tags) / len(tags), 4)  # 0.3 default so seeded prefs stand out
        else:
            s_cat = 0.5  # neutral if no tag

        # ── Final hybrid score ────────────────────────────────
        score = hybrid_score(s_prox, s_svd, s_pop, s_cat)

        results.append({
            "type":        place_type,
            "id":          item_id,
            "name":        c["name"],
            "tag":         tag,
            "distance_m":  int(dist),
            "lat":         float(c["lat"]),
            "lon":         float(c["lon"]),
            "score":       score,
            "score_breakdown": {
                "proximity":        round(s_prox * W_PROXIMITY,  4),
                "svd_predicted":    round(s_svd  * W_SVD,        4),
                "popularity":       round(s_pop  * W_POPULARITY, 4),
                "category_match":   round(s_cat  * W_CATEGORY,   4),
                "svd_raw_estimate": svd_raw,
            }
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
