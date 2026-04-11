-- Add brief description column to places and restaurants
-- Run this after loading the database

ALTER TABLE places ADD COLUMN brief TEXT DEFAULT NULL;
ALTER TABLE restaurants ADD COLUMN brief TEXT DEFAULT NULL;

-- Add some example briefs (you can update these)
UPDATE places SET brief = 'Ancient Egyptian museum with mummies and artifacts' WHERE name ILIKE '%egyptian%museum%';
UPDATE places SET brief = 'Historic Islamic mosque with beautiful architecture' WHERE name ILIKE '%mosque%';
UPDATE places SET brief = 'Beautiful park perfect for relaxation and walking' WHERE name ILIKE '%park%';
UPDATE places SET brief = 'Historic landmark and gathering place' WHERE name ILIKE '%square%';
UPDATE places SET brief = 'Tourist attraction with scenic views' WHERE name ILIKE '%viewpoint%';

UPDATE restaurants SET brief = 'Traditional Egyptian street food, famous for koshari' WHERE name ILIKE '%koshari%';
UPDATE restaurants SET brief = 'Egyptian cuisine, casual dining' WHERE name ILIKE '%gad%' OR name ILIKE '%gaad%';
UPDATE restaurants SET brief = 'Mediterranean and Middle Eastern dishes' WHERE cuisine ILIKE '%mediterranean%';
UPDATE restaurants SET brief = 'Italian cuisine and international flavors' WHERE cuisine ILIKE '%italian%';
UPDATE restaurants SET brief = 'Fresh seafood and grilled specialties' WHERE cuisine ILIKE '%seafood%';

-- Verify
SELECT COUNT(*) as places_with_brief FROM places WHERE brief IS NOT NULL;
SELECT COUNT(*) as restaurants_with_brief FROM restaurants WHERE brief IS NOT NULL;
