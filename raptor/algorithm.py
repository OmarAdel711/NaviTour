from raptor.config import MAX_ROUNDS
from raptor.utils import sec_to_time, time_to_sec
class Label:
    __slots__ = ("stop", "time", "transfers", "prev", "mode")

    def __init__(self, stop, time, transfers, prev=None, mode=None):
        self.stop = stop          # stop index of this label
        self.time = time          # arrival time at this stop
        self.transfers = transfers
        self.prev = prev          # previous Label object
        self.mode = mode          # trip_id or "WALK"


def dominates(a, b):
    return a.time <= b.time and a.transfers <= b.transfers

def pareto_insert(bag, new_label):
    # discard if dominated
    for l in bag:
        if dominates(l, new_label):
            return False
    # remove dominated labels
    bag[:] = [l for l in bag if not dominates(new_label, l)]
    bag.append(new_label)
    return True

def mc_raptor(network ,source_id, target_id, departure_time):

    stop_id_to_idx = network.stop_id_to_idx
    stop_to_trips  = network.stop_to_trips
    trip_stop_times = network.trip_stop_times
    trip_stop_index = network.trip_stop_index
    walk_transfers = network.walk_transfers
    n_stops = network.n_stops
    
    source = stop_id_to_idx[source_id]
    target = stop_id_to_idx[target_id]
    dep = time_to_sec(departure_time)

    # Bags: B[r][p]
    B = [[[] for _ in range(n_stops)] for _ in range(MAX_ROUNDS + 1)]
    # B[0][source].append(Label(dep, 0))
    B[0][source].append(Label(stop=source, time=dep, transfers=0, prev=None, mode=None))

    marked = {source}

    for r in range(1, MAX_ROUNDS + 1):
        # inherit previous round
        for p in range(n_stops):
            B[r][p] = B[r-1][p].copy()

        new_marked = set()
        used_trips = set()

        # -------- Transit phase --------
        for p in marked:
            for trip in stop_to_trips.get(p, []):
                if trip in used_trips:
                    continue

                idx = trip_stop_index[trip].get(p)
                if idx is None:
                    continue

                seq = trip_stop_times[trip]
                for lbl in B[r-1][p]:
                    board_time = seq[idx][1]
                    if board_time < lbl.time:
                        continue

                    last = p
                    for s, arr_t, _ in seq[idx+1:]:

                        new_label = Label(
                            stop=s,               # current stop index
                            time=arr_t,
                            transfers=lbl.transfers + 1,
                            prev=lbl,             # previous Label
                            mode=trip             # trip_id
                        )

                        
                        if pareto_insert(B[r][s], new_label):
                            new_marked.add(s)
                        last = s

                used_trips.add(trip)

        # -------- Walking phase --------
        for p in new_marked.copy():
            for to_p, wt in walk_transfers.get(p, []):
                for lbl in B[r][p]:


                    new_label = Label(
                        stop=to_p,
                        time=lbl.time + wt,
                        transfers=lbl.transfers,
                        prev=lbl,
                        mode="WALK"
                    )
                    if pareto_insert(B[r][to_p], new_label):
                        new_marked.add(to_p)

        marked = new_marked
        if not marked:
            break

    return B, target
