# -*- coding: utf-8 -*-
"""
Created on Fri Feb 27 21:35:34 2026

@author: Samia
"""

import folium
import numpy as np

class RouteVisualizer:
    def __init__(self, stops_df, shapes_df):
        """
        stops_df  → GTFS stops DataFrame
        shapes_df → GTFS shapes DataFrame
        """
        self.stops_df = stops_df
        self.shapes_df = shapes_df

        # Build stop_id → (lat, lon) dictionary
        self.stop_coords = {
            row['stop_id']: (row['stop_lat'], row['stop_lon'])
            for _, row in stops_df.iterrows()
        }

    # ---------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------

    def _nearest_shape_index(self, shape_pts, lat, lon):
        d = (shape_pts[:, 0] - lat) ** 2 + (shape_pts[:, 1] - lon) ** 2
        return np.argmin(d)

    def _expand_leg_with_shape(self, leg):
        # WALK → straight line
        if leg['mode'] == "WALK":
            return [[
                self.stop_coords[leg['from_stop']],
                self.stop_coords[leg['to_stop']]
            ]]

        shape_id = leg.get("shape_id")

        # No geometry → fallback straight line
        if shape_id is None:
            return [[
                self.stop_coords[leg['from_stop']],
                self.stop_coords[leg['to_stop']]
            ]]

        shape = self.shapes_df[self.shapes_df.shape_id == shape_id]

        if shape.empty:
            return [[
                self.stop_coords[leg['from_stop']],
                self.stop_coords[leg['to_stop']]
            ]]

        pts = shape[['shape_pt_lat', 'shape_pt_lon']].values

        lat1, lon1 = self.stop_coords[leg['from_stop']]
        lat2, lon2 = self.stop_coords[leg['to_stop']]

        i1 = self._nearest_shape_index(pts, lat1, lon1)
        i2 = self._nearest_shape_index(pts, lat2, lon2)

        if i1 > i2:
            i1, i2 = i2, i1

        return [pts[i1:i2 + 1].tolist()]

    # ---------------------------------------------------
    # Public function
    # ---------------------------------------------------

    def plot_path(self, path, center=(30.0444, 31.2357), zoom=12):
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="OpenStreetMap"
        )

        for leg in path:
            segments = self._expand_leg_with_shape(leg)

            for seg in segments:
                color = "gray" if leg['mode'] == "WALK" else "blue"
                dash = "5,5" if leg['mode'] == "WALK" else None

                folium.PolyLine(
                    seg,
                    color=color,
                    weight=6,
                    dash_array=dash,
                    tooltip=(
                        "WALK"
                        if leg['mode'] == "WALK"
                        else f"{leg.get('route_short','')} – {leg.get('route_long','')}"
                    )
                ).add_to(m)

        return m