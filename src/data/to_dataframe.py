from pathlib import Path
import json

import pandas as pd



def build_locations_dataframe(locations_root):
	"""
	Builds a dataframe from saved location folders.

	Expected structure:
	  <locations_root>/<location_id>/metadata.json
	  <locations_root>/<location_id>/cubemap/{front,back,left,right,up,down}.jpg
	"""
	locations_path = Path(locations_root)
	if not locations_path.exists():
		return pd.DataFrame(
			columns=[
				"location_id",
				"pano_id",
				"lat",
				"lon",
				"metadata_path",
			]
		)

	rows = []

	for location_dir in sorted(locations_path.iterdir()):
		if not location_dir.is_dir():
			continue

		metadata_path = location_dir / "metadata.json"
		if not metadata_path.exists():
			continue

		with open(metadata_path, "r", encoding="utf-8") as file:
			metadata = json.load(file)

		location = metadata.get("location", {})

		row = {
			"location_id": location_dir.name,
			"pano_id": metadata.get("pano_id"),
			"lat": location.get("lat"),
			"lon": location.get("lng"),
			"metadata_path": str(metadata_path),
		}
		rows.append(row)

	return pd.DataFrame(rows)




def save_locations_dataframe(dataframe, output_csv_path, question):
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
	# add question to dataframe
	dataframe["question"] = question
    dataframe.to_csv(output_path, index=False)
