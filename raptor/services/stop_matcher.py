# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 16:16:49 2026

@author: Samia
"""

# raptor/services/stop_matcher.py

from collections import defaultdict
from rapidfuzz import process, fuzz
from shared.arabic_text import normalize_arabic
from raptor.output_translation import load_translations
from raptor.services.geo_utils import get_lat_lon_from_api, find_nearest_stop


POPULAR_STOP_ALIASES = {
    normalize_arabic("التحرير"): normalize_arabic("ميدان التحرير"),
    normalize_arabic("ميدان التحرير"): normalize_arabic("ميدان التحرير"),
    normalize_arabic("العباسية"): normalize_arabic("العباسية"),
    normalize_arabic("العباسيه"): normalize_arabic("العباسية"),
    normalize_arabic("رمسيس"): normalize_arabic("رمسيس"),
}

class StopMatcher:
    """
    Match user Arabic input to stop_id using translations.
    Provides suggestions if no exact match.
    Ensures returned stop_id exists in network.stop_id_to_idx.
    """

    def __init__(self, network, translations_path):
        """
        network: RAPTOR network object
        translations_path: path to translations.txt
        """
        self.network = network
        self.stop_index = defaultdict(list)
        self.stop_priority = {}

        # Load Arabic translations
        stop_name_func = load_translations(translations_path, network)

        # Build Arabic index from the network DataFrame
        for _, stop in network.stops.iterrows():
            stop_id = stop['stop_id']  # ✅ prefixed S_ / M_
            english_name = str(stop.get('stop_name', '') or '')
            arabic_name = stop_name_func(stop_id)
            stop_idx = self.network.stop_id_to_idx.get(stop_id)
            trip_count = len(self.network.stop_to_trips.get(stop_idx, [])) if stop_idx is not None else 0
            # Prefer metro stops, then highly connected stops.
            self.stop_priority[stop_id] = (
                1 if str(stop_id).startswith("M_") else 0,
                trip_count
            )

            if arabic_name:
                norm_name = normalize_arabic(arabic_name)
                if stop_id not in self.stop_index[norm_name]:
                    self.stop_index[norm_name].append(stop_id)

            if english_name:
                norm_english = normalize_arabic(english_name)
                if stop_id not in self.stop_index[norm_english]:
                    self.stop_index[norm_english].append(stop_id)

        # Keep list of normalized names for fuzzy matching
        self.stop_names = list(self.stop_index.keys())

    def _sorted_stop_ids(self, stop_ids):
        return sorted(
            dict.fromkeys(stop_ids),
            key=lambda stop_id: self.stop_priority.get(stop_id, (0, 0)),
            reverse=True
        )

    @staticmethod
    def _dedupe_preserve_order(stop_ids):
        return list(dict.fromkeys(stop_ids))

    def match_candidates(self, user_input, threshold=80, max_candidates=4, max_distance_km=1.5):
        """
        Returns a ranked list of candidate stop_ids for a user query.
        Exact normalized names are preferred, then partial matches, then fuzzy matches,
        and finally geocoding fallback if nothing local is found.
        """
        norm_input = normalize_arabic(user_input)
        norm_input = POPULAR_STOP_ALIASES.get(norm_input, norm_input)
        candidates = []

        exact_ids = self.stop_index.get(norm_input, [])
        if exact_ids:
            candidates.extend(self._sorted_stop_ids(exact_ids))

        if len(candidates) < max_candidates and norm_input:
            partial_names = [
                name for name in self.stop_names
                if name != norm_input and norm_input in name
            ]
            partial_names.sort(key=lambda name: (
                abs(len(name) - len(norm_input)),
                -len(self.stop_index.get(name, []))
            ))
            for name in partial_names:
                candidates.extend(self._sorted_stop_ids(self.stop_index.get(name, [])))
                if len(self._dedupe_preserve_order(candidates)) >= max_candidates:
                    break

        if len(self._dedupe_preserve_order(candidates)) < max_candidates:
            fuzzy_matches = process.extract(
                norm_input,
                self.stop_names,
                scorer=fuzz.WRatio,
                limit=max_candidates
            )
            for match, score, _ in fuzzy_matches:
                if score < threshold:
                    continue
                candidates.extend(self._sorted_stop_ids(self.stop_index.get(match, [])))
                if len(self._dedupe_preserve_order(candidates)) >= max_candidates:
                    break

        ranked = self._dedupe_preserve_order(candidates)[:max_candidates]
        if ranked:
            return ranked

        coords = get_lat_lon_from_api(user_input)
        if coords:
            nearest_stop_id = find_nearest_stop(self.network, coords, max_distance_km)
            if nearest_stop_id:
                print(f"⚠️ Fallback: using nearest stop '{nearest_stop_id}' for input '{user_input}'")
                return [nearest_stop_id]

        print(f"❌ Could not find stop for input '{user_input}'")
        return []

    def match(self, user_input, threshold=80):
        """
        Returns stop_id if fuzzy match succeeds, else None
        """
        candidates = self.match_candidates(user_input, threshold=threshold, max_candidates=1)
        return candidates[0] if candidates else None

    def match_with_fallback(self, user_input, threshold=80, max_distance_km=1.5):
        """
        Returns a valid stop_id:
        1. Fuzzy match in Arabic
        2. If not found, fallback to nearest stop using geocoding API
        """
        candidates = self.match_candidates(
            user_input,
            threshold=threshold,
            max_candidates=1,
            max_distance_km=max_distance_km
        )
        return candidates[0] if candidates else None

    def match_with_suggestions(self, user_input, threshold=80, max_suggestions=3):
        """
        Returns dict:
        - type: "matched" or "suggestions"
        - stop_id: if matched
        - suggestions: list of close matches if not
        """
        norm_input = normalize_arabic(user_input)

        matches = process.extract(
            norm_input,
            self.stop_names,
            scorer=fuzz.ratio,
            limit=max_suggestions
        )

        best_match, best_score, _ = matches[0]

        if best_score >= threshold:
            stop_id = self._sorted_stop_ids(self.stop_index[best_match])[0]
            if stop_id in self.network.stop_id_to_idx:
                return {"type": "matched", "stop_id": stop_id}

        suggestions = [m[0] for m in matches]
        return {"type": "suggestions", "suggestions": suggestions}
