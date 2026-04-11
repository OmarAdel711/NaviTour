--- ============================================================
-- UPDATE cuisine for all NULL / bad-value rows
-- Based on restaurant names + known data
-- ============================================================

UPDATE restaurants SET cuisine = CASE restaurant_id

    -- ── Cafes & Pastry ───────────────────────────────────────
    WHEN 1   THEN 'cafe;pastry'           -- بوتيه بالميرا       (Palmyra Boutique – French-style cafe/patisserie)
    WHEN 2   THEN 'cafe;pastry'           -- شنتيي               (Chantilly – French patisserie chain Egypt)
    WHEN 12  THEN 'cafe;pastry'           -- لارين               (Larine – cafe & pastry)
    WHEN 21  THEN 'cafe;international'    -- جراند كافيه         (Grand Cafe chain)
    WHEN 24  THEN 'cafe;pastry'           -- لو نوتر             (Le Notre – French patisserie franchise)
    WHEN 158 THEN 'cafe;coffee_shop'      -- Caribou             (Caribou Coffee chain)
    WHEN 196 THEN 'cafe'                  -- El Zahraa Cafe
    WHEN 232 THEN 'cafe;pastry'           -- Peak A Boo          (cafe & dessert, Maadi)
    WHEN 251 THEN 'cafe;international'    -- Restaurant Marasi Cafe
    WHEN 270 THEN 'cafe;international'    -- Crave               (cafe & all-day dining, Cairo)
    WHEN 281 THEN 'cafe;international'    -- Fizze               (cafe & drinks)
    WHEN 282 THEN 'cafe;international'    -- Viola               (cafe & brunch spot)

    -- ── Fast Food Chains ────────────────────────────────────
    WHEN 5   THEN 'chicken;fastfood'      -- كي أف سي            (KFC)
    WHEN 268 THEN 'burger;fastfood'       -- Burger king

    -- ── Burgers ─────────────────────────────────────────────
    WHEN 176 THEN 'burger'               -- سلطان البرگر
    WHEN 267 THEN 'burger'               -- Bazooka              (burger chain)
    WHEN 272 THEN 'burger'               -- Budz                 (burger spot, New Cairo)
    WHEN 280 THEN 'burger;american'      -- Streeks              (smash burgers)

    -- ── Pizza ───────────────────────────────────────────────
    WHEN 9   THEN 'pizza;italian'        -- فويغو                (Fuego – pizza & Italian)
    WHEN 111 THEN 'pizza'               -- بيتزا بيت العيلة
    WHEN 113 THEN 'pizza'               -- بيتزا كينج
    WHEN 141 THEN 'pizza'               -- دوبل ديز بيتزا - فرع مدينة نصر
    WHEN 229 THEN 'pizza'               -- Take n Bake           (pizza, Maadi)
    WHEN 237 THEN 'pizza'               -- Elwali Pizza and Pie - بيتزا وفطائر الوالي
    WHEN 240 THEN 'pizza'               -- بيتزا المختار

    -- ── Italian ─────────────────────────────────────────────
    WHEN 117 THEN 'italian'             -- Tavola                (Italian chain Egypt)
    WHEN 276 THEN 'italian'             -- توم اند بسل           (Tom & Basil – Italian)

    -- ── Egyptian ────────────────────────────────────────────
    WHEN 53  THEN 'egyptian'            -- نعمة                  (Egyptian cuisine)
    WHEN 54  THEN 'egyptian'            -- كشرى الدبور           (koshary)
    WHEN 55  THEN 'egyptian'            -- الشبراوى              (El Shabrawy chain)
    WHEN 56  THEN 'egyptian'            -- الوادى
    WHEN 68  THEN 'egyptian'            -- الجحش                 (was Egyptian_beans – fix tag)
    WHEN 69  THEN 'egyptian'            -- الجحش
    WHEN 75  THEN 'egyptian'            -- الشبراوي              (was bad tag 'الشبراوي')
    WHEN 95  THEN 'egyptian'            -- مطعم خير              (was bad tag 'مطعم_خير')
    WHEN 96  THEN 'egyptian'            -- فلافل غازي            (falafel & ful – Egyptian street food)
    WHEN 99  THEN 'egyptian'            -- مطعم الخيرات
    WHEN 102 THEN 'egyptian'            -- Eish wa Malh          (Egyptian – bread & salt)
    WHEN 112 THEN 'egyptian'            -- المنسى
    WHEN 123 THEN 'egyptian'            -- فطيرة                 (feteer meshaltet)
    WHEN 124 THEN 'egyptian'            -- الشبراوي              (El Shabrawy branch)
    WHEN 138 THEN 'egyptian'            -- كبدة ومخ النعمانى     (liver & brain – Egyptian street)
    WHEN 139 THEN 'egyptian'            -- آخر ساعة              (Egyptian diner)
    WHEN 154 THEN 'egyptian'            -- مطعم الزعيم للكشري   (koshary)
    WHEN 162 THEN 'egyptian'            -- كشرى ال مؤمن وجحا    (koshary)
    WHEN 168 THEN 'egyptian'            -- كشري السلطان          (koshary)
    WHEN 173 THEN 'egyptian'            -- مطعم فول و طعمية      (ful & falafel)
    WHEN 179 THEN 'egyptian'            -- مطعم ارض الحضارة
    WHEN 183 THEN 'egyptian'            -- ملك الكبدة            (liver – Egyptian street)
    WHEN 187 THEN 'egyptian'            -- كشرى زيزو             (koshary)
    WHEN 191 THEN 'egyptian'            -- مطعم الشيف سرحان
    WHEN 205 THEN 'kebab;grill'         -- كبابجي ومشويات علاء الدين
    WHEN 207 THEN 'egyptian'            -- كشري افندينا          (koshary)
    WHEN 248 THEN 'egyptian'            -- Elsonny               (Egyptian – El Sonny chain)
    WHEN 255 THEN 'egyptian'            -- سعد الحرامي           (Egyptian sandwich/liver)
    WHEN 256 THEN 'egyptian'            -- مطعم فول ام عادل      (ful & falafel)
    WHEN 257 THEN 'egyptian'            -- محمد المنوفي          (Egyptian kebab/liver)
    WHEN 258 THEN 'egyptian'            -- مطعم بجه              (Egyptian offal/breakfast)
    WHEN 259 THEN 'egyptian'            -- مطعم اورمة فهمي
    WHEN 261 THEN 'egyptian'            -- مطعم بحه              (Egyptian offal)
    WHEN 263 THEN 'egyptian'            -- كشري الغباشي          (koshary)

    -- ── Grill & Kebab ───────────────────────────────────────
    WHEN 62  THEN 'grill;kebab'         -- مطعم أبو شقرة        (Abu Shakra – famous Egyptian grill)
    WHEN 70  THEN 'grill;kebab'         -- Sobhy El Haty         (كباب صبحي الحاتي – iconic chain)
    WHEN 71  THEN 'kebab'               -- Kabab Shaker
    WHEN 100 THEN 'regional;egyptian'   -- العائلات              (family Egyptian restaurant)
    WHEN 101 THEN 'grill;kebab'         -- مطعم و حاتى الإمام
    WHEN 105 THEN 'grill;kebab'         -- مطعم حمزه
    WHEN 106 THEN 'kebab'               -- كبابجي الطيب
    WHEN 114 THEN 'kebab'               -- كبابجي الزهراء
    WHEN 140 THEN 'grill;kebab'         -- حاتي اولاد سليمان
    WHEN 142 THEN 'kebab'               -- مطعم قصر الكبابجى
    WHEN 149 THEN 'grill'               -- مشويات الرايق
    WHEN 150 THEN 'kebab'               -- كبابجى الشيخ ريحان
    WHEN 197 THEN 'grill;kebab'         -- صبحى كابر
    WHEN 260 THEN 'grill;kebab'         -- مطعم رأفت
    WHEN 273 THEN 'kebab;grill'         -- مطعم محمد رفاعي الكبابجي
    WHEN 288 THEN 'grill'               -- شواية الميرلاند

    -- ── Seafood ─────────────────────────────────────────────
    WHEN 22  THEN 'seafood'             -- سوق السمك
    WHEN 89  THEN 'seafood'             -- مطعم اسماك
    WHEN 92  THEN 'seafood'             -- ملك الجمبري           (shrimp restaurant)
    WHEN 125 THEN 'seafood'             -- اسماك القبه
    WHEN 170 THEN 'seafood'             -- مطعم أبو العربى للمأكولات البحرية
    WHEN 186 THEN 'seafood'             -- اسماك دهب             (was 'local' – seafood restaurant)

    -- ── Chicken ─────────────────────────────────────────────
    WHEN 93  THEN 'chicken'             -- THE فراخ

    -- ── Chinese ─────────────────────────────────────────────
    WHEN 14  THEN 'chinese'             -- نيل بيكينغ            (Nile Peking – Chinese)
    WHEN 46  THEN 'chinese'             -- ماندرين قويدر         (Mandarin Qweidr – Chinese)
    WHEN 94  THEN 'chinese'             -- مطعم بيكينج           (Peking restaurant)

    -- ── Arabic / Lebanese / Syrian ──────────────────────────
    WHEN 17  THEN 'syrian;arab'         -- زهرة الشام            (Syrian cuisine)
    WHEN 19  THEN 'lebanese'            -- دار القمر             (Lebanese chain)
    WHEN 43  THEN 'lebanese'            -- Cairut                (Lebanese – Cairo Beirut)
    WHEN 45  THEN 'egyptian'            -- El Menofy             (Egyptian – Menoufiya style)
    WHEN 153 THEN 'lebanese'            -- تبولة                 (Tabbouleh – Lebanese chain)
    WHEN 210 THEN 'arab;regional'       -- Bab El-Sharq
    WHEN 218 THEN 'arab;regional'       -- Shubak Habibi
    WHEN 241 THEN 'arab;regional'       -- Baytal Qadi
    WHEN 244 THEN 'regional;egyptian'   -- مطعم السوق
    WHEN 250 THEN 'syrian;arab'         -- مطعم إبن الشام        (Ibn El Sham – Syrian)

    -- ── Indian ──────────────────────────────────────────────
    WHEN 135 THEN 'indian'              -- Shiva Indian Restaurant

    -- ── Indonesian ──────────────────────────────────────────
    WHEN 129 THEN 'asian;indonesian'    -- Rumah Makan Sabiek
    WHEN 134 THEN 'asian;indonesian'    -- Rumah Makan Bandung

    -- ── Japanese / Asian ────────────────────────────────────
    WHEN 169 THEN 'japanese;asian'      -- Sachi                 (Japanese fusion)
    WHEN 283 THEN 'japanese;asian'      -- TAIYAKI               (Japanese street food)

    -- ── International / Multi-cuisine ───────────────────────
    WHEN 15  THEN 'international'       -- Grand Cafe
    WHEN 18  THEN 'international'       -- DUO
    WHEN 27  THEN 'international'       -- spectra
    WHEN 29  THEN 'regional;egyptian'   -- نادي سيهورس           (Seahorse club – Egyptian regional)
    WHEN 38  THEN 'arab;regional'       -- Rihan
    WHEN 39  THEN 'international'       -- Dishes
    WHEN 64  THEN 'international'       -- مطعم سبكترا
    WHEN 73  THEN 'international'       -- Spectra
    WHEN 104 THEN 'international'       -- ريفيري                (Reverie – international)
    WHEN 116 THEN 'international'       -- Nile Point
    WHEN 118 THEN 'grill;regional'      -- Andrea                (Andrea El Mariouteya style)
    WHEN 126 THEN 'international'       -- Tycoon
    WHEN 127 THEN 'international'       -- باتيو فود هب          (Patio Food Hub – food court style)
    WHEN 157 THEN 'international'       -- Tivoli Dome
    WHEN 166 THEN 'international'       -- Lake View
    WHEN 172 THEN 'regional'            -- About basem restaurant
    WHEN 192 THEN 'international'       -- Hippopotamus          (French-international chain)
    WHEN 230 THEN 'international'       -- Sponta
    WHEN 238 THEN 'international'       -- Tasha                 (modern international, Zamalek)
    WHEN 262 THEN 'regional'            -- مطعم حبايب السيده
    WHEN 264 THEN 'regional'            -- مطعم بلدياتي

    -- ── American ────────────────────────────────────────────
    WHEN 16  THEN 'american'            -- تي جي أي أف           (TGI Fridays)
    WHEN 128 THEN 'american'            -- Virginian

    -- ── French / European ───────────────────────────────────
    WHEN 160 THEN 'french'              -- لبيسترو               (Le Bistro – French)
    WHEN 215 THEN 'french;european'     -- Caprice               (French bistro, Maadi)
    WHEN 222 THEN 'french'              -- Bistor Paris

    -- ── Latin American ──────────────────────────────────────
    WHEN 77  THEN 'latin_american'      -- Caracas               (Venezuelan/Latin)
    WHEN 231 THEN 'latin_american'      -- Tabla Luna - Latin American Cuisine

    -- ── Mexican ─────────────────────────────────────────────
    WHEN 20  THEN 'mexican'             -- Salimos

    -- ── Yemeni ──────────────────────────────────────────────
    WHEN 156 THEN 'yemeni'              -- باب المندب يمني
    WHEN 175 THEN 'yemeni'              -- مطعم اليمن السعيد
    WHEN 254 THEN 'yemeni'              -- مطعم حضر موت عنتر

    -- ── African / Sudanese ──────────────────────────────────
    WHEN 133 THEN 'african;sudanese'    -- Altukol Sudanese

    -- ── Vegan ───────────────────────────────────────────────
    WHEN 219 THEN 'vegan'               -- Vegan in Our House

    -- ── Sandwich / Street food ──────────────────────────────
    WHEN 152 THEN 'egyptian'            -- Very cheap local food (falafel)
    WHEN 171 THEN 'sandwich'            -- مطعم وح وح للسندوتشات
    WHEN 255 THEN 'egyptian'            -- سعد الحرامي

    -- ── Dessert / Cake ──────────────────────────────────────
    WHEN 284 THEN 'cake;dessert'        -- Crazy Shake 'n Cake

    -- ── Fast casual / Food hubs ─────────────────────────────
    WHEN 161 THEN 'regional'            -- فسحة سمية
    WHEN 184 THEN 'fastfood'            -- مطعم fries&pasta      (was وجبات_سريعه – fix tag)
    WHEN 193 THEN 'lebanese;arab'       -- Al Hamra street       (Lebanese-Arab, same strip as 195)
    WHEN 220 THEN 'international'       -- Via 82
    WHEN 224 THEN 'regional'            -- االمنتزة السياحي لشركة مصر الجديدة للاسكان والتعمير
    WHEN 247 THEN 'egyptian;regional'   -- طبخه                  (was 'local' – home-style Egyptian)
    WHEN 253 THEN 'grill;bakery'        -- سمايلز جريل ، زاكسي بيكري
    WHEN 286 THEN 'arab;regional'       -- Al dahan              (Egyptian/Gulf style grills)
    WHEN 287 THEN 'pizza'               -- What the crust        (pizza spot)
    WHEN 289 THEN 'egyptian;regional'   -- ع الباب               (Egyptian street food)

    -- ── Russian / Yacht ─────────────────────────────────────
    WHEN 178 THEN 'international'       -- яхта                  (Yacht restaurant)

    -- ── El Omda ─────────────────────────────────────────────
    WHEN 131 THEN 'egyptian'            -- El Omda               (Egyptian chain)

END
WHERE restaurant_id IN (
    1, 2, 5, 9, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 27, 29,
    38, 39, 43, 45, 46, 53, 54, 55, 56, 62, 64, 68, 69, 70, 71, 73, 74, 75,
    77, 89, 92, 93, 94, 95, 96, 99, 100, 101, 102, 104, 105, 106, 111, 112,
    113, 114, 116, 117, 118, 123, 124, 125, 126, 127, 128, 129, 131, 133, 134,
    135, 138, 139, 140, 141, 142, 149, 150, 152, 153, 154, 156, 157, 158, 160,
    161, 162, 166, 167, 168, 169, 170, 171, 172, 173, 175, 176, 178, 179, 183,
    184, 186, 187, 191, 192, 193, 196, 197, 205, 207, 210, 215, 218, 219, 220,
    222, 224, 229, 230, 231, 232, 237, 238, 240, 241, 244, 247, 248, 250, 251,
    253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 267, 268, 270,
    272, 273, 276, 280, 281, 282, 283, 284, 286, 287, 288, 289
);

-- ============================================================
-- SEPARATE fixes for entries that had bad/non-standard values
-- (These already have a cuisine value but it's wrong/messy)
-- ============================================================

-- Fix ID 23: كافيتريا واحة النخيل — Egyptian cafeteria
UPDATE restaurants SET cuisine = 'regional;egyptian' WHERE restaurant_id = 23;

-- Fix ID 74: Weinerwald — Austrian chicken chain
UPDATE restaurants SET cuisine = 'austrian;chicken' WHERE restaurant_id = 74;

-- Fix ID 167: Arabiata — Italian pasta chain
UPDATE restaurants SET cuisine = 'italian' WHERE restaurant_id = 167;
-- Verify:
SELECT COUNT(*) AS still_nan FROM restaurants WHERE cuisine IS NULL OR cuisine = 'NaN';
-- Expected: 0