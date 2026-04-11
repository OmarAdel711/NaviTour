# -*- coding: utf-8 -*-
"""
Created on Thu Feb 26 16:08:26 2026

@author: Samia
"""

# raptor/output_translation.py
from functools import lru_cache
from pathlib import Path
import pandas as pd


METRO_ARABIC_OVERRIDES = {
    "Ain Helwan": "عين حلوان",
    "Ain Shams": "عين شمس",
    "Al-Sayeda Zeinab": "السيدة زينب",
    "Al-Shohadaa": "الشهداء",
    "Attaba": "العتبة",
    "Bohooth": "البحوث",
    "Cairo University": "جامعة القاهرة",
    "Dar El-Salam": "دار السلام",
    "Dokki": "الدقي",
    "El-Demerdash": "الدمرداش",
    "El-Giza": "الجيزة",
    "El-Maasara": "المعصرة",
    "El-Malek El-Saleh": "الملك الصالح",
    "El-Marg": "المرج",
    "El-Matareyya": "المطرية",
    "El-Mounib": "المنيب",
    "El-Zahraa": "الزهراء",
    "Ezbet El-Nakhl": "عزبة النخل",
    "Faisal": "فيصل",
    "Ghamra": "غمرة",
    "Hadayek El-Maadi": "حدائق المعادي",
    "Hadayek Helwan": "حدائق حلوان",
    "Hadayeq El-Zaitoun": "حدائق الزيتون",
    "Hammamat El-Qobba": "حمامات القبة",
    "Helmeyet El-Zaitoun": "حلمية الزيتون",
    "Helwan": "حلوان",
    "Helwan University": "جامعة حلوان",
    "Khalafawy": "الخلفاوي",
    "Kobri El-Qobba": "كوبري القبة",
    "Kolleyyet El-Zeraa": "كلية الزراعة",
    "Kozzika": "كوتسيكا",
    "Maadi": "المعادي",
    "Manshiet El-Sadr": "منشية الصدر",
    "Mar Girgis": "مار جرجس",
    "Masarra": "مسرة",
    "Mezallat": "المظلات",
    "Mohamed Naguib": "محمد نجيب",
    "Nasser": "ناصر",
    "New El-Marg": "المرج الجديدة",
    "Omm El-Misryeen": "أم المصريين",
    "Opera": "الأوبرا",
    "Orabi": "عرابي",
    "Rod El Farag": "روض الفرج",
    "Saad Zaghloul": "سعد زغلول",
    "Sadat": "السادات",
    "Sakanat El-Maadi": "ثكنات المعادي",
    "Sakiat Mekki": "ساقية مكي",
    "Saray El-Qobba": "سراي القبة",
    "Shubra El-Kheima": "شبرا الخيمة",
    "St. Teresa": "سانت تريزا",
    "Tora El-Asmant": "طرة الأسمنت",
    "Tora El-Balad": "طرة البلد",
    "Wadi Hof": "وادي حوف",
}


def _possible_translation_paths(translations_path):
    requested = Path(translations_path)
    project_data_dir = requested.parent

    paths = [
        project_data_dir / "Metro_gtfs" / "translations.txt",
        project_data_dir / "public_gtfs" / "translations.txt",
        requested,
    ]

    unique_paths = []
    for path in paths:
        if path not in unique_paths:
            unique_paths.append(path)

    return unique_paths


@lru_cache(maxsize=8)
def _load_stop_translation_map(translations_path):
    stop_name_ar = {}

    for path in _possible_translation_paths(translations_path):
        if not path.exists():
            continue

        translations = pd.read_csv(path, encoding="utf-8-sig")
        filtered = translations[
            (translations.table_name == "stops") &
            (translations.field_name == "stop_name") &
            (translations.language == "ar")
        ]

        for _, row in filtered.iterrows():
            stop_name_ar[str(row["field_value"])] = str(row["translation"])

    stop_name_ar.update(METRO_ARABIC_OVERRIDES)
    return stop_name_ar


def load_translations(translations_path: str, network) -> dict:
    """
    Load Arabic stop names from the GTFS translation files.
    Priority is:
    1. Metro GTFS translations
    2. Public GTFS translations
    3. Legacy shared translations file

    Built-in metro names remain as a fallback so routing output stays readable
    even if a translation file is missing.
    """
    stop_name_ar = _load_stop_translation_map(translations_path)

    def stop_name(sid):
        en = network.stop_id_to_name.get(sid, sid)
        return stop_name_ar.get(en, en)

    return stop_name


def print_legs(legs, stop_name_func):
    """
    Pretty-print collapsed legs using a stop_name function.
    """
    for leg in legs:
        if leg['mode'] == 'WALK':
            print(
                f"WALK: {stop_name_func(leg['from_stop'])} "
                f"→ {stop_name_func(leg['to_stop'])}"
            )
        else:
            print(
                f"{leg['agency']} | {leg['route_short']} ({leg['route_long']})\n"
                f"  {stop_name_func(leg['from_stop'])} "
                f"→ {stop_name_func(leg['to_stop'])}"
            )


def print_segments(segments, stop_name_func):
    """
    Pretty-print full segments using a stop_name function.
    """
    for seg in segments:
        if seg['mode'] == 'WALK':
            print(
                f"WALK: {stop_name_func(seg['from_stop'])} "
                f"→ {stop_name_func(seg['to_stop'])}"
            )
        else:
            print(
                f"{seg['agency']} | {seg['route_short']} ({seg['route_long']})\n"
                f"  {stop_name_func(seg['from_stop'])} "
                f"→ {stop_name_func(seg['to_stop'])}"
            )
