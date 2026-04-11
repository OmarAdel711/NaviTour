-- ============================================================
-- NaviTour: Places Cleanup Script
-- Generated : 2026-03-09
-- Actions   : 91 deletes | 25 category fixes
-- ============================================================


-- ============================================================
-- STEP 1: DELETE JUNK ENTRIES
-- Personal pins, businesses, companies that leaked from OSM
-- ============================================================

DELETE FROM places WHERE place_id IN (
    24,   -- 'Home'                             [attraction]
    29,   -- 'Coffee shop meeting place'        [attraction]
    32,   -- 'بتروتريد'                          [artwork]
    42,   -- 'مصاري'                             [artwork]
    48,   -- 'هوندا'                             [artwork]
    49,   -- 'شركه رفتراك مصر للتبريد'           [attraction]
    50,   -- 'شركة إيواي للسياحة'                [artwork]
    53,   -- 'بيت ايهاب'                         [attraction]
    56,   -- 'شركة وسط المدينة للتسويق'          [artwork]
    60,   -- 'Work'                              [artwork]
    65,   -- 'Teleperformance - City Walk'       [attraction]
    70,   -- 'اصلاح وصيانة اجهزة اليكترونية'    [artwork]
    72,   -- 'الأندلسية للصناعات الغذائية'       [artwork]
    73,   -- 'مقر سناك شوت'                      [artwork]
    74,   -- 'مقر اكسلوسيف'                      [artwork]
    76,   -- 'شغل'                               [artwork]
    80,   -- 'شقة مصر نصر'                       [attraction]
    82,   -- 'شقة التجمع اشرف'                   [attraction]
    83,   -- 'تويوتا AMG'                        [artwork]
    90,   -- 'مقر العمل'                         [artwork]
    91,   -- 'ابناء الشيخ للالكترونيات'          [artwork]
    149,  -- 'صيانة موتوسيكلات...'               [attraction]
    181,  -- '9002'                              [monument]
    183,  -- '9 قرنفل'                           [memorial]
    184   -- '26'                                [castle]
);


-- ============================================================
-- STEP 2: DELETE BUDDHA DUPLICATES
-- 51 identical 'Buddha' pins all in one sculpture cluster.
-- Keep only ID 102 (the first one), delete the rest.
-- ============================================================

DELETE FROM places WHERE place_id IN (
    103, 104, 105, 106, 107, 108, 109, 110, 111, 112,
    113, 114, 115, 116, 117, 118, 119, 120, 121, 122,
    123, 124, 125, 126, 127, 128, 129, 130, 131, 132,
    133, 134, 135, 136, 137, 138, 139, 140, 141, 142,
    143, 144, 155, 156, 157, 158, 159, 160, 161, 162
);


-- ============================================================
-- STEP 3: DELETE NEIGHBOURHOOD ZONE MARKERS
-- These are OSM zone/area labels, not actual visit destinations
-- ============================================================

DELETE FROM places WHERE place_id IN (
    22,   -- '7ay l 10'                         [attraction]
    23,   -- '5ma'                              [attraction]
    35,   -- 'مترو بنات'                         [attraction]
    62,   -- 'الحى السادس مدينة نصر'             [attraction]
    63,   -- 'الحى السابع مدينة نصر'             [attraction]
    64,   -- 'التبة'                             [attraction]
    66,   -- 'نفق لشارع الثورة'                  [viewpoint]
    67,   -- 'تحت الكوبري للعبور للجهة المقابلة' [viewpoint]
    69,   -- 'موقع العاشر'                       [artwork]
    86    -- 'بريزر'                             [viewpoint]
);


-- ============================================================
-- STEP 4: FIX WRONG CATEGORIES
-- ============================================================

-- Monuments mistaggged as artwork / viewpoint / museum
UPDATE places SET category = 'monument'      WHERE place_id = 2;    -- مسلة المطرية         (was: museum)
UPDATE places SET category = 'monument'      WHERE place_id = 3;    -- باب النصر            (was: viewpoint)
UPDATE places SET category = 'monument'      WHERE place_id = 4;    -- باب المزهرية         (was: viewpoint)
UPDATE places SET category = 'monument'      WHERE place_id = 7;    -- طلعت حرب             (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 36;   -- رمسيس                (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 81;   -- Egyptian Ankh         (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 87;   -- سيمون بوليفار         (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 88;   -- تمثال السيد عمر مكرم  (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 102;  -- Buddha                (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 145;  -- حورس                  (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 151;  -- Sphinx of Thutmosis III (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 152;  -- Sphinx of Thutmosis III (was: artwork)
UPDATE places SET category = 'monument'      WHERE place_id = 153;  -- Auguste Mariette       (was: artwork)

-- Places of worship mistaggged as museum / attraction / castle / mosque
UPDATE places SET category = 'place_of_worship' WHERE place_id = 57;   -- سيدنا الحسين         (was: museum)
UPDATE places SET category = 'place_of_worship' WHERE place_id = 58;   -- السيدة نفيسه         (was: museum)
UPDATE places SET category = 'place_of_worship' WHERE place_id = 68;   -- مسجد صبحي حسين       (was: attraction)
UPDATE places SET category = 'place_of_worship' WHERE place_id = 174;  -- مسجد فاطمة الشربتلي  (was: castle)
UPDATE places SET category = 'place_of_worship' WHERE place_id = 177;  -- Masjid AlPasha        (was: mosque)

-- Gallery mistaggged as attraction
UPDATE places SET category = 'gallery'       WHERE place_id = 54;   -- Attar Art              (was: attraction)

-- Attraction mistaggged
UPDATE places SET category = 'attraction'    WHERE place_id = 10;   -- Rokn Farouk            (was: museum)
UPDATE places SET category = 'attraction'    WHERE place_id = 154;  -- ممشى أهل مصر           (was: artwork)
UPDATE places SET category = 'attraction'    WHERE place_id = 170;  -- ڤيلا أحمد و خالد شحاته (was: castle)

-- Viewpoint mistaggged
UPDATE places SET category = 'viewpoint'     WHERE place_id = 178;  -- حى البنفسج             (was: monument)
UPDATE places SET category = 'viewpoint'     WHERE place_id = 182;  -- الشباب الجنوبى          (was: monument)

-- Historic building mistaggged
UPDATE places SET category = 'historic'      WHERE place_id = 168;  -- المدرسة الصالحية        (was: building)


-- ============================================================
-- STEP 5: VERIFY
-- ============================================================

SELECT
    category,
    COUNT(*) AS total
FROM places
GROUP BY category
ORDER BY total DESC;

-- Expected final totals after cleanup:
-- place_of_worship : ~207  (202 + 5 fixed)
-- monument         : ~20   (7 original + 13 fixed)
-- artwork          : ~42   (93 - 51 Buddha dupes - 13 fixed to monument - artwork fixes)
-- attraction       : ~20
-- museum           : ~12
-- cinema           : 13
-- sports_centre    : 10
-- viewpoint        : ~6
-- gallery          : 4
-- garden           : 4
-- memorial         : 6
-- ruins            : 3
-- arts_centre      : 3
-- park             : 5
-- theatre          : 2
-- theme_park       : 1
-- historic         : 1
-- archaeological_site: 1