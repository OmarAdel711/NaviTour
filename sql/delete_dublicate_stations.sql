-- ============================================================
-- NaviTour: Fix stations table
-- 1. Delete 4 NaN-name rows (IDs 78,79,80,81)
-- 2. Delete duplicate stations (keep lowest ID)
-- ============================================================

-- Step 1: Delete NaN rows
DELETE FROM stations WHERE station_id IN (78, 79, 80, 81);

-- Step 2: Delete duplicate stations (keep lowest ID)
-- محطة الروبيكي: keep 15, delete 67
DELETE FROM stations WHERE station_id = 67;

-- عدلى منصور: keep 57, delete 74 and 88
DELETE FROM stations WHERE station_id IN (74, 88);

-- مدينة الفنون و الثقافة: keep 66, delete 85
DELETE FROM stations WHERE station_id = 85;

-- Verify
SELECT COUNT(*) AS total_stations FROM stations;
SELECT COUNT(*) AS nan_names   FROM stations WHERE name IS NULL OR name = 'NaN';
SELECT COUNT(*) AS dup_names   FROM (
    SELECT name FROM stations GROUP BY name HAVING COUNT(*) > 1
) x;