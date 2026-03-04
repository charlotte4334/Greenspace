''' This code is the central code for the pipeline. 
It is responsible for running the entire pipeline, 
including data preprocessing, api calls, 
saving images and filtering. '''

from src.api.sampler import sample_locations
from config.settings import configs
from src.data.io import save_location_record, save_pano_id
from src.data.to_dataframe import build_locations_dataframe, save_locations_dataframe
from src.api.streetview import api_streetview_metadata, api_streetview_panorama
from src.pairing.location_pairs import create_location_pairs

def run_fetch_data(config):
    """
    Mode 1: fetch data
    """

    # ------------ SAMPLING LOCATIONS ------------
    sampled_points = sample_locations(
        map_data= config["map_type"],
        method=config["sampling_method"],
        n=config["n_samples"],
        plot=True
    )

    # ------------ API CALLS ------------------

    for lat, lon in sampled_points:
        try:
            metadata = api_streetview_metadata(lat, lon)

            if not metadata:
                continue

            pano_id = metadata.get("pano_id")

            cubemap = api_streetview_panorama(pano_id)

            save_location_record(
                locations_root=config["locations_dir"],
                metadata=metadata,
                cubemap_images=cubemap,
            )
            save_pano_id(pano_id)
        except Exception as error:
            continue

    



def run_pipeline():

    mode =  configs["mode"]

    if mode == "fetching_data":
        run_fetch_data(configs)
    elif mode == "building_dataframe":
        dataframe = build_locations_dataframe(locations_root=configs["locations_dir"])
        save_locations_dataframe(dataframe, output_csv_path=configs["locations_index_csv"])

    elif mode == "pairing": 
            create_location_pairs(configs)

    else:
        raise ValueError(f"Unknown mode: {mode}")


