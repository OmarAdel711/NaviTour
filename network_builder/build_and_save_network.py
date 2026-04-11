import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import pickle
from network_builder.network_preprocessing import build_network

m_dir = os.path.join(BASE_DIR, "data", "Metro_gtfs")
s_dir = os.path.join(BASE_DIR, "data", "public_gtfs")
network_path = os.path.join(BASE_DIR, "data", "network.pkl")


print("Building network (this may take a while)...")

network = build_network(
    m_dir=m_dir,
    s_dir=s_dir
)

with open(network_path, "wb") as f:
    pickle.dump(network, f)

print("Network saved successfully!")