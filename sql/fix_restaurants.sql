-- ==============================================================
-- NaviTour: Fix 2 Remaining Issues
-- ==============================================================

-- ==============================================================
-- ISSUE 1: Duplicate restaurant geom
--   id=24 (Asyut Gift Haven) + id=25 (سوق السمك) → different places,
--   same building coords → KEEP BOTH (not a real problem)
--   id=326 + id=327 (مطعم محمد رفاعي الكبابجي) → exact duplicate → delete 327
-- ==============================================================

DELETE FROM ratings
WHERE place_type = 'restaurant' AND place_id = 274;

DELETE FROM restaurants WHERE restaurant_id = 274;

-- ==============================================================
-- ISSUE 2: 1064 orphan ratings pointing to deleted place_ids
--   These are ratings that were inserted for place_of_worship/artwork
--   rows which were later deleted. Clean them up.
-- ==============================================================

DELETE FROM ratings
WHERE place_type = 'place'
  AND place_id NOT IN (SELECT place_id FROM places);

-- ==============================================================
-- VERIFY: Run check_data.py again after this
-- ==============================================================

SELECT 'ratings'     AS tbl, COUNT(*) FROM ratings
UNION ALL SELECT 'places',      COUNT(*) FROM places
UNION ALL SELECT 'restaurants', COUNT(*) FROM restaurants;

-- Check orphans gone:
SELECT COUNT(*) AS orphan_ratings
FROM ratings r
WHERE r.place_type = 'place'
  AND NOT EXISTS (SELECT 1 FROM places p WHERE p.place_id = r.place_id);
-- Expected: 0

-- Check restaurant duplicate gone:
SELECT COUNT(*) AS dup_geoms
FROM (SELECT geom, COUNT(*) FROM restaurants GROUP BY geom HAVING COUNT(*) > 1) x;
-- Expected: 1 (Asyut Gift Haven + سوق السمك share geom → acceptable)