# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 15:32:54 2026

@author: Samia
"""

import pandas as pd


def time_to_sec(t):
    h, m, s = map(int, t.split(":"))
    return h * 3600 + m * 60 + s


def stoptimes_frequency_expansion(path):
    stop_times = pd.read_csv(path + "/stop_times.txt")
    frequencies = pd.read_csv(path + "/frequencies.txt")
    
    # 2. Convert times to seconds
    stop_times['arr_sec'] = stop_times['arrival_time'].apply(time_to_sec)
    stop_times['dep_sec'] = stop_times['departure_time'].apply(time_to_sec)
    
    # 3. Expand frequency trips
    expanded_rows = []
    
    freq_trip_ids = set(frequencies.trip_id)
    
    for _, freq in frequencies.iterrows():
        trip_id = freq['trip_id']
        start = time_to_sec(freq['start_time'])
        end = time_to_sec(freq['end_time'])
        headway = int(freq['headway_secs'])
    
        base_trip = stop_times[stop_times['trip_id'] == trip_id].sort_values("stop_sequence")
        if base_trip.empty:
            continue
    
        base_start = base_trip.iloc[0]['dep_sec']
        t = start
        k = 0
    
        while t <= end:
            shift = t - base_start
            new_trip_id = f"{trip_id}_FREQ_{k}"
    
            for _, row in base_trip.iterrows():
                expanded_rows.append({
                    "trip_id": new_trip_id,
                    "stop_id": row['stop_id'],
                    "stop_sequence": row['stop_sequence'],
                    "arr_sec": row['arr_sec'] + shift,
                    "dep_sec": row['dep_sec'] + shift
                })
            k += 1
            t += headway
    
    expanded_stop_times = pd.DataFrame(expanded_rows)
    
    # Add non-frequency trips back
    expanded_stop_times = pd.concat([
        expanded_stop_times,
        stop_times[~stop_times.trip_id.isin(freq_trip_ids)][
            ["trip_id", "stop_id", "stop_sequence", "arr_sec", "dep_sec"]
        ]
    ], ignore_index=True)
    
    return expanded_stop_times


def trips_frequency_expasion(path, expanded_stop_times):
    trips = pd.read_csv(path + "/trips.txt")
    # after expansion
    new_trips = []
    
    for freq_trip_id in expanded_stop_times['trip_id'].unique():
        # extract original route_id
        base_trip_id = freq_trip_id.split("_FREQ_")[0]
        route_id = trips.loc[trips.trip_id == base_trip_id, 'route_id'].values[0]
        shape_id = trips.loc[trips.trip_id == base_trip_id, 'shape_id'].values[0]
    
        new_trips.append({
            "trip_id": freq_trip_id,
            "route_id": route_id,
            "shape_id" : shape_id
        })

    expanded_trips_df = pd.DataFrame(new_trips)
    trips_combined = pd.concat([trips, expanded_trips_df], ignore_index=True)
    return trips_combined
