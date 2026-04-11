import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from collections import defaultdict
from raptor.config import MAX_WALK, WALK_SPEED, EARTH_RADIUS
from network_builder.GTFS_preprocessing import stoptimes_frequency_expansion, trips_frequency_expasion



class Network:
    def __init__(self):
        self.stops = None
        self.stop_times = None
        self.trips = None
        self.shapes = None
        self.stop_to_trips = None
        self.trip_stop_times = None
        self.trip_stop_index = None
        self.walk_transfers = None
        self.stop_id_to_idx = None
        self.idx_to_stop_id = None
        self.n_stops = None
        self.trip_to_route = None
        self.route_info = None
        self.trip_to_shape = None
        self.stop_id_to_name = None

def build_network(m_dir, s_dir):
    net = Network()

    # ------------------ Load data ------------------
    surface_stops = pd.read_csv(s_dir + "/stops.txt")
    metro_stops   = pd.read_csv(m_dir + "/stops.txt")
    
    surface_stop_times = stoptimes_frequency_expansion(s_dir)
    metro_stop_times   = stoptimes_frequency_expansion(m_dir)
    
    surface_trips = trips_frequency_expasion(s_dir, surface_stop_times)
    metro_trips   = trips_frequency_expasion(m_dir, metro_stop_times)
    
    M_routes = pd.read_csv(m_dir + "/routes.txt")  
    S_routes = pd.read_csv(s_dir + "/routes.txt")  
    
    S_shapes = pd.read_csv(s_dir + "/shapes.txt")
    M_shapes = pd.read_csv(m_dir + "/shapes.txt")
    # ------------------ Namespace stop IDs ------------------
    surface_stops['stop_id'] = "S_" + surface_stops.stop_id.astype(str)
    metro_stops['stop_id']   = "M_" + metro_stops.stop_id.astype(str)
    
    surface_stop_times['stop_id'] = "S_" + surface_stop_times.stop_id.astype(str)
    metro_stop_times['stop_id']   = "M_" + metro_stop_times.stop_id.astype(str)
    
    # ------------------ Combine feeds ------------------
    stops = pd.concat([surface_stops, metro_stops], ignore_index=True)
    stop_times = pd.concat([surface_stop_times, metro_stop_times], ignore_index=True)
    trips = pd.concat([surface_trips, metro_trips], ignore_index=True)
    shapes = pd.concat([M_shapes,S_shapes], ignore_index=True)
    
    # ------------------ Stop indexing ------------------
    stops_list = stops['stop_id'].astype(str).tolist()
    stop_id_to_idx = {sid: i for i, sid in enumerate(stops_list)}
    idx_to_stop_id = {i: sid for sid, i in stop_id_to_idx.items()}
    n_stops = len(stops_list)
    
    # ------------------ Stop id to name ------------------
    stop_id_to_name = dict(
    zip(stops['stop_id'].astype(str), stops['stop_name'])
    )
    # ------------------ Trip preprocessing ------------------
    trip_stop_times = {}
    trip_stop_index = {}
    stop_to_trips = defaultdict(set)
    
    trips['trip_id'] = trips['trip_id'].astype(str)
    stop_times['trip_id'] = stop_times['trip_id'].astype(str)
    
    for _, row in stop_times.iterrows():
        trip = row['trip_id']
        stop_idx = stop_id_to_idx[row['stop_id']]
        arr_sec = row['arr_sec']
        dep_sec = row['dep_sec']
    
        trip_stop_times.setdefault(trip, []).append((stop_idx, arr_sec, dep_sec))
        stop_to_trips[stop_idx].add(trip)
    
    for trip, seq in trip_stop_times.items():
        seq.sort(key=lambda x: x[1])
        trip_stop_index[trip] = {s: i for i, (s, _, _) in enumerate(seq)}
    
    # ------------------ Trip → Route mapping ------------------
    routes = pd.concat([S_routes, M_routes], ignore_index=True)
    
    # ------------------ Map trips to routes ------------------
    trip_to_route = trips.set_index('trip_id')['route_id'].to_dict()

    route_info = routes.set_index('route_id')[['agency_id', 'route_short_name', 'route_long_name']].to_dict('index')
    
    # ------------------ Map trips to shape ------------------
    shapes.sort_values(
        ["shape_id", "shape_pt_sequence"],
        inplace=True
    )
    trip_to_shape = trips.set_index("trip_id")["shape_id"].to_dict()
    
    # ------------------ STOP → ROUTES  ------------------
    stop_to_routes = defaultdict(set)
    
    for trip, seq in trip_stop_times.items():
        route = trip_to_route.get(trip)
        if route is None:
            continue
        for stop, _, _ in seq:
            stop_to_routes[stop].add(route)
    
    # ------------------ Build walking transfers  ------------------
    coords = np.radians(stops[['stop_lat', 'stop_lon']].values)
    tree = BallTree(coords, metric='haversine')
    radius = MAX_WALK / EARTH_RADIUS
    neighbors = tree.query_radius(coords, r=radius)
    
    walk_transfers = defaultdict(list)
    
    for i, neigh in enumerate(neighbors):
        for j in neigh:
            if i == j:
                continue
    
            # BLOCK walking between stops sharing any route
            if stop_to_routes[i] & stop_to_routes[j]:
                continue
    
            d = EARTH_RADIUS * np.linalg.norm(coords[i] - coords[j])
            walk_time = int(d / WALK_SPEED)
            walk_transfers[i].append((j, walk_time))

    # ------------------ Assign everything to Network object ------------------
    net.stops = stops
    net.stop_times = stop_times
    net.trips = trips
    net.shapes = shapes
    net.stop_to_trips = stop_to_trips
    net.trip_stop_times = trip_stop_times
    net.trip_stop_index = trip_stop_index
    net.walk_transfers = walk_transfers
    net.stop_id_to_idx = stop_id_to_idx
    net.idx_to_stop_id = idx_to_stop_id
    net.n_stops = n_stops
    net.trip_to_route = trip_to_route
    net.route_info = route_info
    net.trip_to_shape = trip_to_shape
    net.stop_id_to_name = stop_id_to_name

    return net