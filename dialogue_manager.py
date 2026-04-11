# dialogue_manager.py
# الدمج الكامل: المودل يفهم الكلام + GPS حقيقي + RAPTOR

import os, sys, requests, pickle, re, json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from states import State
from raptor.services.raptor_service import run_raptor_plan_from_assistant_json
from raptor.services.geo_utils import find_nearest_stop, haversine
from raptor.utils import format_legs
from raptor.output_translation import load_translations


NETWORK_PATH = os.path.join(BASE_DIR, "data", "network.pkl")
TRANSLATIONS_PATH = os.path.join(BASE_DIR, "data", "translations.txt")
LOCATION_SERVICE_URL = os.getenv(
    "NAVITOUR_LOCATION_SERVICE_URL",
    "http://127.0.0.1:5000/get_location"
)


CAIRO_MIN_LAT, CAIRO_MAX_LAT = 29.8, 30.3
CAIRO_MIN_LON, CAIRO_MAX_LON = 31.0, 31.6

AGENCY_LABELS = {
    "Metro": "مترو الأنفاق",
    "NAT": "مترو الأنفاق",
    "CTA": "هيئة النقل العام",
    "CTA_M": "ميكروباص هيئة النقل",
    "P_O_14": "أتوبيس عام",
    "P_B_8": "أتوبيس عام",
    "MM": "أتوبيس حضري",
    "COOP": "أتوبيس تعاوني",
    "GRN": "أتوبيس أخضر",
    "BOX": "أتوبيس خاص",
    "LTRA_M": "خط إقليمي",
}


# ─────────────────────────────────────────
# تحميل الشبكة
# ─────────────────────────────────────────

_network = None


def _rebuild_network():
    from network_builder.network_preprocessing import build_network

    m_dir = os.path.join(BASE_DIR, "data", "Metro_gtfs")
    s_dir = os.path.join(BASE_DIR, "data", "public_gtfs")
    network = build_network(m_dir=m_dir, s_dir=s_dir)

    with open(NETWORK_PATH, "wb") as f:
        pickle.dump(network, f)

    return network

def get_network():
    global _network
    if _network is None:
        try:
            with open(NETWORK_PATH, "rb") as f:
                _network = pickle.load(f)
        except Exception as e:
            print(f"[NETWORK] Failed to load pickle ({e}). Rebuilding from GTFS...")
            _network = _rebuild_network()
            print("[NETWORK] Rebuild complete and saved.")
    return _network


# ─────────────────────────────────────────
# تحميل المودل
# ─────────────────────────────────────────

_tokenizer = None
_model = None
_llm_ready = False
_llm_disabled = os.getenv("NAVITOUR_ENABLE_LLM", "0").lower() not in {"1", "true", "yes", "on"}
_llm_failed = False


def _load_llm():

    global _tokenizer, _model, _llm_ready, _llm_failed

    if _llm_disabled or _llm_failed:
        return False

    if _llm_ready:
        return True

    try:

        from cairo_assistant.model_manager import get_models

        _, _tokenizer, _model = get_models()

        _llm_ready = True

        print("[LLM] Model loaded")

        return True

    except Exception as e:

        print("[LLM] Model not available:", e)
        _llm_failed = True

        return False


# ─────────────────────────────────────────
# استخراج intent من المودل
# ─────────────────────────────────────────

def _llm_extract(user_message):

    if not _load_llm():
        return None, False

    try:

        from cairo_assistant.assistant_core import ask_cairo_assistant

        response, is_nav = ask_cairo_assistant(user_message, _tokenizer, _model)

        if not is_nav:
            return None, False

        json_match = re.search(r'\{.*\}', response.replace('\n', ''))

        if not json_match:
            return None, False

        parsed = json.loads(json_match.group())

        if "start_point" in parsed and "end_point" in parsed:

            parsed["intent"] = "navigation"

            return parsed, True

    except Exception as e:

        print("LLM extraction error:", e)

    return None, False


def _llm_answer_general(user_message):

    if not _load_llm():
        return None

    try:

        from cairo_assistant.assistant_core import ask_cairo_assistant

        response, is_nav = ask_cairo_assistant(user_message, _tokenizer, _model)

        if not is_nav:
            return response

    except Exception:
        pass

    return None


# ─────────────────────────────────────────
# GPS
# ─────────────────────────────────────────

def get_live_location():

    try:

        res = requests.get(LOCATION_SERVICE_URL, timeout=3)

        data = res.json()

        if data["lat"] is None:
            return None

        return float(data["lat"]), float(data["lon"])

    except Exception:
        return None


def _nearest_stop_info(user_lat, user_lon):

    network = get_network()

    stop_id = find_nearest_stop(network, (user_lat, user_lon), max_distance_km=5.0)

    if stop_id is None:
        return None

    stop_row = network.stops[network.stops['stop_id'] == stop_id].iloc[0]

    dist_m = round(
        haversine(
            user_lat,
            user_lon,
            stop_row['stop_lat'],
            stop_row['stop_lon']
        ) * 1000
    )

    stop_name_func = load_translations(TRANSLATIONS_PATH, network)

    arabic_name = stop_name_func(stop_id)

    link = (
        f"https://www.openstreetmap.org/directions"
        f"?engine=fossgis_osrm_foot"
        f"&route={user_lat},{user_lon};{stop_row['stop_lat']},{stop_row['stop_lon']}"
    )

    return arabic_name, dist_m, link


# ─────────────────────────────────────────
# تحسين عرض الرحلة
# ─────────────────────────────────────────

def format_route_text(route_text):

    cleaned_lines = []
    for raw_line in route_text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _describe_leg_transport(leg):

    if leg.get("mode") == "WALK":
        return "🚶 امشِ مسافة قصيرة"

    route_short = (leg.get("route_short") or "").strip()
    agency = leg.get("agency")
    agency_label = AGENCY_LABELS.get(agency, agency or "مواصلات عامة")

    upper_route = route_short.upper()
    is_metro_route = bool(re.fullmatch(r"[LM]\d+", upper_route))
    if agency in {"Metro", "NAT"} or is_metro_route:
        return f"🚇 اركب المترو {route_short}".strip()

    if route_short:
        return f"🚌 اركب {agency_label} - خط {route_short}"

    return f"🚌 اركب {agency_label}"


# ─────────────────────────────────────────
# RAPTOR
# ─────────────────────────────────────────

def _run_raptor(assistant_json, departure_time, network=None):

    if network is None:
        network = get_network()

    plan_or_error = run_raptor_plan_from_assistant_json(
        network,
        assistant_json,
        departure_time=departure_time
    )

    if isinstance(plan_or_error, dict) and "error" in plan_or_error:
        return f"⚠️ {plan_or_error.get('message','لا يوجد طريق')}", None

    if isinstance(plan_or_error, str) and plan_or_error.startswith("Error"):
        return f"⚠️ {plan_or_error}", None

    legs_or_error = plan_or_error["legs"]
    route_summary = plan_or_error.get("summary", {})
    route_options = plan_or_error.get("route_options", [])

    stop_name_func = load_translations(TRANSLATIONS_PATH, network)

    lines = []
    map_legs = []

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")

    for i, leg in enumerate(legs_or_error):

        from_name = stop_name_func(leg['from_stop'])
        to_name   = stop_name_func(leg['to_stop'])
        step      = i + 1

        # إحداثيات المحطات للخريطة
        from_row = network.stops[network.stops['stop_id'] == leg['from_stop']]
        to_row   = network.stops[network.stops['stop_id'] == leg['to_stop']]

        map_leg = {
            "mode":      leg['mode'],
            "agency":    leg.get('agency'),
            "route_short": leg.get('route_short'),
            "route_long": leg.get('route_long'),
            "stops":     leg.get('stops', []),
            "from_name": from_name,
            "to_name":   to_name,
            "from_stop": leg['from_stop'],
            "to_stop":   leg['to_stop'],
            "from_lat":  float(from_row.iloc[0]['stop_lat']) if not from_row.empty else None,
            "from_lon":  float(from_row.iloc[0]['stop_lon']) if not from_row.empty else None,
            "to_lat":    float(to_row.iloc[0]['stop_lat'])   if not to_row.empty   else None,
            "to_lon":    float(to_row.iloc[0]['stop_lon'])   if not to_row.empty   else None,
        }
        map_legs.append(map_leg)

        lines.append(f"\nالخطوة {step} {_describe_leg_transport(leg)}")
        lines.append(f"   من: {from_name}")
        lines.append(f"   إلى: {to_name}")
        if leg['mode'] != 'WALK' and leg.get('route_long'):
            lines.append(f"   المسار: {leg['route_long']}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines), {
        "legs": map_legs,
        "summary": route_summary,
        "route_options": route_options,
    }


def _parse_time(raw):

    raw = (raw or "").strip()

    if not raw or raw == "دلوقتي":
        return datetime.now().strftime("%H:%M:%S")

    if ":" in raw and len(raw) <= 5:
        return raw + ":00"

    return "08:00:00"


def _extract_time_hint(message):

    message = (message or "").strip()

    if not message:
        return None

    if "دلوقتي" in message:
        return "دلوقتي"

    match = re.search(r"\b(\d{1,2}:\d{2})\b", message)
    if match:
        return match.group(1)

    return None


def _strip_navigation_prefixes(text):

    text = (text or "").strip(" ؟?.,،")
    prefixes = [
        "عايز اروح",
        "عايز أروح",
        "اروح",
        "أروح",
        "رايح",
        "عايز اوصل",
        "عايز أوصل",
        "اوصل",
        "أوصل",
        "وديني",
        "روحني",
    ]

    lowered = text.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip(" ؟?.,،")

    return text


def _extract_destination_hint(message):

    message = (message or "").strip()
    if not message:
        return None

    cleaned = re.sub(r"\b\d{1,2}:\d{2}\b", "", message).replace("دلوقتي", "").strip(" ؟?.,،")

    patterns = [
        r"(?:الى|إلى)\s+(.+)$",
        r"(?:ل|لـ)\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            candidate = match.group(1).strip(" ؟?.,،")
            if candidate:
                return candidate

    candidate = _strip_navigation_prefixes(cleaned)
    return candidate or None


def _extract_route_points_from_text(message):

    message = (message or "").strip()
    if not message:
        return None, None

    cleaned = re.sub(r"\b\d{1,2}:\d{2}\b", "", message).replace("دلوقتي", "").strip(" ؟?.,،")
    compact = re.sub(r"\s+", " ", cleaned)
    stripped = _strip_navigation_prefixes(compact)
    stripped = re.sub(r"^(?:ازاي|إزاي)\s+", "", stripped, flags=re.IGNORECASE)

    def _clean_point(value):
        value = (value or "").strip(" ؟?.,،")
        if value.startswith("ل") and len(value) > 1 and not value.startswith("ال"):
            value = "ال" + value[1:]
        return value

    patterns = [
        (r"(?:انا|أنا)\s+في\s+(.+?)\s+.*?(?:اروح|أروح|اوصل|أوصل|إلى|الى|ل|لـ)\s+(.+)$", "start_first"),
        (r"^من\s+(.+?)\s+(?:(?:إلى|الى)\s+|ل(?:ـ)?)(.+)$", "start_first"),
        (r"(.+?)\s+من\s+(.+)$", "destination_first"),
    ]

    for pattern, mode in patterns:
        candidate_text = compact if "انا" in pattern or "أنا" in pattern else stripped
        match = re.search(pattern, candidate_text, flags=re.IGNORECASE)
        if not match:
            continue

        first = _clean_point(match.group(1))
        second = _clean_point(match.group(2))

        if mode == "start_first":
            return first or None, second or None
        return second or None, first or None

    match = re.search(r"(.+?)\s+(?:(?:إلى|الى)\s+|ل(?:ـ)?)(.+)$", stripped, flags=re.IGNORECASE)
    if match:
        start_name = _clean_point(match.group(1))
        destination_name = _clean_point(match.group(2))
        return start_name or None, destination_name or None

    return None, None


def _is_navigation_request(message):

    message = (message or "").strip()
    if not message:
        return False

    nav_triggers = (
        "اروح", "أروح", "رايح", "وديني", "اوصل", "أوصل", "طريق",
        "ازاي", "إزاي", "محطة", "مواصل", "من", "الى", "إلى"
    )

    return any(trigger in message for trigger in nav_triggers)


# ─────────────────────────────────────────
# مدير الحوار
# ─────────────────────────────────────────

class DialogueManager:

    def __init__(self, live_location_provider=None):

        self.state = State.IDLE
        self.start_location = None
        self.destination = None
        self.time = None
        self.last_legs = None   # آخر legs من RAPTOR عشان الخريطة ترسمها
        self.last_route_summary = None
        self.last_route_options = None
        self.last_route_context = None
        self.live_location_provider = live_location_provider
        self.used_live_location = False

    def reset_conversation(self):

        self.state = State.IDLE
        self.start_location = None
        self.destination = None
        self.time = None
        self.last_legs = None
        self.last_route_summary = None
        self.last_route_options = None
        self.last_route_context = None
        self.used_live_location = False

    def _greeting_text(self):

        return (
            "أهلاً بيك في NaviTour 👋\n"
            "اكتب لي المكان اللي عايز تروحه، ولو الـ GPS شغال أقدر أبدأ من موقعك الحالي تلقائياً.\n"
            "مثال: عايز أروح رمسيس من العباسية."
        )

    def _nearest_stop_from_live_location(self):

        try:
            location = self.live_location_provider() if self.live_location_provider else get_live_location()
        except Exception:
            location = None
        if location is None:
            return None, "⚠️ مش قادر أحدد موقعك الحالي. فعّل الـ GPS أو اكتب نقطة البداية."

        user_lat, user_lon = location

        inside_cairo = (
            CAIRO_MIN_LAT <= user_lat <= CAIRO_MAX_LAT and
            CAIRO_MIN_LON <= user_lon <= CAIRO_MAX_LON
        )

        if not inside_cairo:
            return None, "📍 يبدو أنك خارج نطاق القاهرة حالياً، اكتب نقطة البداية يدويًّا."

        stop_info = _nearest_stop_info(user_lat, user_lon)
        if stop_info is None:
            return None, "⚠️ لم أجد محطة قريبة من موقعك الحالي."

        arabic_name, dist_m, link = stop_info
        return {
            "name": arabic_name,
            "distance_m": dist_m,
            "map_link": link,
        }, None

    def _build_route_reply(self, start_name, destination_name, departure_time_raw, include_live_location_summary=False):

        departure_time = _parse_time(departure_time_raw)
        assistant_json = {
            "intent": "navigation",
            "start_point": {"official_name_ar": start_name},
            "end_point": {"official_name_ar": destination_name},
        }

        route_lines, route_plan = _run_raptor(assistant_json, departure_time)
        self.last_legs = route_plan["legs"] if route_plan else None
        self.last_route_summary = route_plan.get("summary") if route_plan else None
        self.last_route_options = route_plan.get("route_options") if route_plan else None
        self.last_route_context = {
            "start_name": start_name,
            "destination_name": destination_name,
            "departure_time": departure_time,
            "used_live_location": include_live_location_summary,
        }

        if route_plan is None:
            return route_lines

        route_lines = format_route_text(route_lines)
        header = f"🧭 أفضل طريق من {start_name} إلى {destination_name}\n\n"
        summary_lines = []
        if self.last_route_summary:
          duration_minutes = self.last_route_summary.get("duration_minutes")
          transfers = self.last_route_summary.get("transfers")
          arrival_time = self.last_route_summary.get("arrival_time")
          if duration_minutes is not None:
              summary_lines.append(f"⏱️ الوقت التقريبي: {duration_minutes} دقيقة")
          if transfers is not None:
              summary_lines.append(f"🔁 عدد التحويلات: {transfers}")
          if arrival_time:
              summary_lines.append(f"🕒 الوصول المتوقع: {arrival_time}")

        route = header
        if summary_lines:
            route += "\n".join(summary_lines) + "\n\n"
        route += route_lines

        if self.last_route_options and len(self.last_route_options) > 1:
            route += f"\n\n🗺️ على الخريطة هتلاقي {len(self.last_route_options)} اختيارات للمسار، والاختيار المقترح ظاهر أولاً."

        if not include_live_location_summary:
            return route

        nearest_stop, location_error = self._nearest_stop_from_live_location()
        if nearest_stop is None:
            return route + ("\n\n" + location_error if location_error else "")

        return (
            route +
            f"\n\n📍 أقرب محطة ليك: {nearest_stop['name']}\n"
            f"🚶 المسافة: {nearest_stop['distance_m']} متر تقريبًا\n\n"
            f"🗺️ افتح الخريطة:\n{nearest_stop['map_link']}"
        )

    def _complete_route(self):

        reply = self._build_route_reply(
            self.start_location,
            self.destination,
            self.time or "دلوقتي",
            include_live_location_summary=self.used_live_location
        )

        self.state = State.IDLE
        self.start_location = None
        self.destination = None
        self.time = None
        self.used_live_location = False

        return reply

    def _try_full_navigation_from_llm(self, message):

        assistant_json, used_llm = _llm_extract(message)
        if assistant_json is None:
            return None

        start_name = assistant_json.get("start_point", {}).get("official_name_ar")
        destination_name = assistant_json.get("end_point", {}).get("official_name_ar")
        if not start_name or not destination_name:
            return None

        return self._build_route_reply(
            start_name,
            destination_name,
            _extract_time_hint(message) or "دلوقتي"
        )


    def process(self, message):

        message = (message or "").strip()
        self.last_legs = None
        self.last_route_summary = None
        self.last_route_options = None
        self.last_route_context = None

        if not message:
            if self.state == State.AWAITING_DESTINATION:
                return "تحب تروح فين؟"
            if self.state == State.AWAITING_START:
                return "اكتب نقطة البداية، أو فعّل الـ GPS وأنا أحدد أقرب محطة ليك."
            if self.state == State.AWAITING_TIME:
                return "هتتحرك امتى؟ اكتب دلوقتي أو وقت مثل 08:30."
            return self._greeting_text()

        lowered = message.lower()
        if lowered in {"reset", "ابدأ من جديد", "اعادة", "إعادة", "الغاء", "إلغاء"}:
            self.reset_conversation()
            return self._greeting_text()

        if self.state == State.AWAITING_DESTINATION:
            self.destination = message
            nearest_stop, location_error = self._nearest_stop_from_live_location()
            if nearest_stop is not None:
                self.start_location = nearest_stop["name"]
                self.time = "دلوقتي"
                self.used_live_location = True
                return self._complete_route()

            self.state = State.AWAITING_START
            self.used_live_location = False
            return (
                f"تمام، هنروح {self.destination}.\n"
                f"{location_error}\n"
                "اكتب نقطة البداية."
            )

        if self.state == State.AWAITING_START:
            time_hint = _extract_time_hint(message)
            cleaned_start = re.sub(r"\b\d{1,2}:\d{2}\b", "", message).replace("دلوقتي", "").strip(" ؟?.,،")
            self.start_location = cleaned_start or message
            self.used_live_location = False
            if time_hint:
                self.time = time_hint
                return self._complete_route()

            self.state = State.AWAITING_TIME
            return "هتتحرك امتى؟\n(اكتب: دلوقتي أو وقت مثل 08:30)"

        if self.state == State.AWAITING_TIME:
            self.time = message
            return self._complete_route()

        full_navigation_reply = self._try_full_navigation_from_llm(message)
        if full_navigation_reply:
            self.state = State.IDLE
            self.start_location = None
            self.destination = None
            self.time = None
            return full_navigation_reply

        if _is_navigation_request(message):
            parsed_start, parsed_destination = _extract_route_points_from_text(message)
            self.start_location = parsed_start
            self.destination = parsed_destination or _extract_destination_hint(message)
            self.time = _extract_time_hint(message) or "دلوقتي"

            if self.start_location and self.destination:
                self.used_live_location = False
                return self._complete_route()

            if self.destination:
                nearest_stop, location_error = self._nearest_stop_from_live_location()
                if nearest_stop is not None:
                    self.start_location = nearest_stop["name"]
                    self.used_live_location = True
                    return self._complete_route()

                self.state = State.AWAITING_START
                self.used_live_location = False
                return (
                    f"تمام، هنروح {self.destination}.\n"
                    f"{location_error}\n"
                    "اكتب نقطة البداية، مثلاً: العباسية."
                )

            self.state = State.AWAITING_DESTINATION
            return "محتاج أعرف الوجهة أولاً. تحب تروح فين؟"

        llm_answer = _llm_answer_general(message)

        if llm_answer:
            return llm_answer

        return "ممكن تقولّي رايح فين أو تسألني عن أقرب محطة 🚇"
