'''

Here we create a modulable set of pairs to compare 

Methods: 
- random sparse graph

- ring and random augmentation

- Trueskill system??

- Batch-wise
                                                                                                                                   
'''

import random
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from config.settings import configs

def create_location_pairs(configs):

    method = configs["pairing_method"]

    # load locations dataframe 

    dataframe = pd.read_csv(configs["locations_index_csv"])
    
    k = configs["random_graph_k"]
    min_distance = configs["min_pair_distance_m"]

    if method == "random_spatial_sparse_graph":
        # have a test graph of 100 connected graohs
        '''if configs["test"]:
            dataframe = dataframe.head(100)
            k= 
            '''
        pairs = random_sparse_graph(dataframe, k, min_distance)

        Path(configs["ranking_dir"]).mkdir(parents=True, exist_ok=True)
        print("Saving N = {} pairs to {}".format(len(pairs), configs["locations_pairs_csv"]))
        pairs.to_csv(configs["locations_pairs_csv"], index=False)
        return pairs

    raise ValueError(f"Unknown pairing method: {method}")



def random_sparse_graph(dataframe, k, min_distance):

    '''
    Create random sparse graph of location pairs. 
    Does not directly compare locations at less than 40m distance.
    k is the number of comparisons per location

    returns dataframe with columns: pano_id1,lat1,lng1, pano_id2, lat2, lng2
    '''
    n = len(dataframe)
    coords = np.radians(dataframe[["lat", "lon"]].values) # convert lat/lng to radians

    #build KD tree for efficient neighbor search
    tree = KDTree(coords)

    pairs = set() # to store unique pairs
    for i in range(n):
        radius = min_distance / 6371000 # convert 40m to radians

        neighbors_within_radius = tree.query_ball_point(coords[i], r=radius) # neighbors within min distance
        neighbors_within_radius = set(neighbors_within_radius)
        indices = [idx for idx in range(n) if idx != i and idx not in neighbors_within_radius] # exclude self and too-close neighbors


        if len(indices) > 0:

            # sample k neighbors from indices
            selected = random.sample(indices, min(k, len(indices)))

            for j in selected:
                p1 = dataframe.iloc[i]["pano_id"]
                p2 = dataframe.iloc[j]["pano_id"]
                pair = tuple(sorted((p1, p2))) # sort to avoid duplicates
                pairs.add(pair)
    
    # convert pairs to dataframe
    id_map = dataframe.set_index("pano_id").to_dict("index")

    pair_rows = []
    for p1, p2 in pairs:
        pair_rows.append([id_map[p1]["location_id"],
                         id_map[p2]["location_id"]])

    return pd.DataFrame(pair_rows, columns=["Loc_1", "Loc_2"])
