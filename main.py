# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 15:07:48 2026

@author: Samia
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from raptor.services.raptor_service import run_raptor_from_assistant_json
from raptor.services.map_visualizer import RouteVisualizer
from raptor.utils import format_legs
import pickle
import webbrowser


# Load network once
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NETWORK_PATH = os.path.join(BASE_DIR, "data", "network.pkl")

with open(NETWORK_PATH, "rb") as f:
    network = pickle.load(f)
    
    
assistant_json = {
    "intent": "navigation",
    "start_point": {"official_name_ar": "العباسية", "official_name_en": "Abbaseya"},
    "end_point": {"official_name_ar": "رمسيس", "official_name_en": "Ramses"}
}

legs_or_error = run_raptor_from_assistant_json(network,assistant_json)

if isinstance(legs_or_error, dict) and "error" in legs_or_error:
    print("❗", legs_or_error["message"])
    if "suggestions" in legs_or_error:
        print("💡 Suggestions:", legs_or_error["suggestions"])
else:
    for leg in format_legs(legs_or_error):
        print(leg)
 
        

if not isinstance(legs_or_error, dict):
    visualizer = RouteVisualizer(
        network.stops,
        network.shapes
    )

    m = visualizer.plot_path(legs_or_error)
    m.save("cairo_real_route.html")
    webbrowser.open("cairo_real_route.html")
