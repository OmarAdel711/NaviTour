# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 16:17:18 2026

@author: Samia
"""

# raptor/services/raptor_service.py

from collections import OrderedDict
from copy import deepcopy
from raptor.algorithm import mc_raptor
from raptor.utils import extract_solutions, reconstruct, collapse_to_legs, sec_to_time, time_to_sec
from raptor.output_translation import load_translations, print_legs, print_segments
from raptor.services.stop_matcher import StopMatcher

import os as _os
translations_path = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))),
    "data", "translations.txt"
)

_DEBUG_ROUTING = _os.getenv("NAVITOUR_DEBUG_ROUTING", "").lower() in {"1", "true", "yes", "on"}
_CACHE_WINDOW_SECONDS = int(_os.getenv("NAVITOUR_ROUTE_CACHE_WINDOW_SECONDS", "300"))
_CACHE_MAX_ENTRIES = int(_os.getenv("NAVITOUR_ROUTE_CACHE_MAX_ENTRIES", "128"))
_ROUTE_OPTIONS_LIMIT = int(_os.getenv("NAVITOUR_ROUTE_OPTIONS_LIMIT", "3"))
_matcher_cache = {}
_translation_func_cache = {}
_route_plan_cache = OrderedDict()


def _cache_key_for_departure_time(departure_time: str) -> str:
    total_seconds = time_to_sec(departure_time)
    rounded_seconds = total_seconds - (total_seconds % _CACHE_WINDOW_SECONDS)
    return sec_to_time(rounded_seconds)


def _normalize_route_cache_key(start_name: str, end_name: str, departure_time: str):
    return (start_name.strip(), end_name.strip(), _cache_key_for_departure_time(departure_time))


def _get_cached_stop_matcher(network):
    key = id(network)
    matcher = _matcher_cache.get(key)
    if matcher is None:
        matcher = StopMatcher(network, translations_path)
        _matcher_cache[key] = matcher
    return matcher


def _get_cached_stop_name_func(network):
    key = id(network)
    stop_name_func = _translation_func_cache.get(key)
    if stop_name_func is None:
        stop_name_func = load_translations(translations_path, network)
        _translation_func_cache[key] = stop_name_func
    return stop_name_func


def _get_cached_route_plan(cache_key):
    cached = _route_plan_cache.get(cache_key)
    if cached is None:
        return None
    _route_plan_cache.move_to_end(cache_key)
    return deepcopy(cached)


def _store_cached_route_plan(cache_key, plan):
    _route_plan_cache[cache_key] = deepcopy(plan)
    _route_plan_cache.move_to_end(cache_key)
    while len(_route_plan_cache) > _CACHE_MAX_ENTRIES:
        _route_plan_cache.popitem(last=False)


def _legs_signature(legs):
    signature_parts = []
    for leg in legs or []:
        signature_parts.append(
            "|".join([
                str(leg.get("mode") or ""),
                str(leg.get("agency") or ""),
                str(leg.get("route_short") or ""),
                str(leg.get("trip_id") or ""),
                str(leg.get("from_stop") or ""),
                str(leg.get("to_stop") or ""),
                str(len(leg.get("stops") or [])),
            ])
        )
    return "||".join(signature_parts)


def _build_route_option(solution, network, departure_time, origin_id, destination_id):
    segments = reconstruct(solution, network)
    legs = collapse_to_legs(segments)
    departure_seconds = time_to_sec(departure_time)
    duration_seconds = max(solution.time - departure_seconds, 0)
    transit_legs = sum(1 for leg in legs if leg["mode"] == "TRANSIT")
    walk_legs = sum(1 for leg in legs if leg["mode"] == "WALK")
    return {
        "legs": legs,
        "summary": {
            "departure_time": departure_time,
            "arrival_time": sec_to_time(solution.time),
            "duration_seconds": duration_seconds,
            "duration_minutes": max(1, round(duration_seconds / 60)) if duration_seconds else 0,
            "transfers": max(transit_legs - 1, 0),
            "transit_legs": transit_legs,
            "walk_legs": walk_legs,
            "origin_stop_id": origin_id,
            "destination_stop_id": destination_id,
        }
    }


def _route_option_sort_key(option):
    summary = option.get("summary") or {}
    return (
        summary.get("duration_seconds", 0),
        summary.get("transfers", 0),
        summary.get("walk_legs", 0),
        len(option.get("legs") or []),
    )


def run_raptor_plan_from_assistant_json(network, assistant_json, departure_time="08:00:00"):
    """
    Runs RAPTOR from Cairo assistant JSON.
    Returns a dict with route legs and summary metadata or an error message.
    """

    # -----------------------------
    # Initialize StopMatcher
    # -----------------------------
    start_name = assistant_json.get("start_point", {}).get("official_name_ar")
    end_name = assistant_json.get("end_point", {}).get("official_name_ar")

    if not start_name or not end_name:
        return "Error: Missing origin or destination names"

    cache_key = _normalize_route_cache_key(start_name, end_name, departure_time)
    cached_plan = _get_cached_route_plan(cache_key)
    if cached_plan is not None:
        return cached_plan

    # -----------------------------
    # Initialize helpers
    # -----------------------------
    stop_matcher = _get_cached_stop_matcher(network)

    # -----------------------------
    # Match names to network stop IDs
    # -----------------------------
    origin_candidates = stop_matcher.match_candidates(start_name)
    destination_candidates = stop_matcher.match_candidates(end_name)

    if not origin_candidates or not destination_candidates:
        return f"Error: Could not find valid stops for '{start_name}' or '{end_name}'"
    origin_id = origin_candidates[0]
    destination_id = destination_candidates[0]

    try:
        B, target = mc_raptor(network, origin_id, destination_id, departure_time)
    except KeyError as e:
        return f"Error: RAPTOR KeyError for stop {e}"

    solutions = extract_solutions(B, target)
    if not solutions:
        return "Error: No solution found"

    ranked_solutions = sorted(solutions, key=lambda label: (label.time, label.transfers))
    route_options = []
    seen_signatures = set()

    for solution in ranked_solutions:
        option = _build_route_option(solution, network, departure_time, origin_id, destination_id)
        signature = _legs_signature(option["legs"])
        if not signature or signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        route_options.append(option)
        if len(route_options) >= _ROUTE_OPTIONS_LIMIT:
            break

    if not route_options:
        return "Error: No solution found"

    route_options.sort(key=_route_option_sort_key)
    best_option = route_options[0]

    if _DEBUG_ROUTING:
        print(f" Using stop {origin_id} for origin '{start_name}'")
        print(f" Using stop {destination_id} for destination '{end_name}'")

    # -----------------------------
    # Load stop translations for readable output
    # -----------------------------
    stop_name_func = _get_cached_stop_name_func(network)
    
    if _DEBUG_ROUTING:
        print_legs(best_option["legs"], stop_name_func)
        print_segments(reconstruct(ranked_solutions[0], network), stop_name_func)

    plan = {
        "legs": best_option["legs"],
        "summary": best_option["summary"],
        "route_options": route_options,
    }
    _store_cached_route_plan(cache_key, plan)
    return plan


def run_raptor_from_assistant_json(network, assistant_json, departure_time="08:00:00"):
    """
    Backward-compatible wrapper that returns only route legs or an error message.
    """
    plan = run_raptor_plan_from_assistant_json(network, assistant_json, departure_time)
    if isinstance(plan, str):
        return plan
    return plan["legs"]
