from pathlib import Path
import json
from typing import Dict

import pandas as pd
from PIL import Image

from config.settings import PANO_IDS_FILE


CUBEMAP_FACES = ("front", "back", "left", "right", "up", "down")


# ---------- CSV ----------

def save_csv(df, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_csv(path):
    return pd.read_csv(path)


# ---------- JSON ----------

def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# ---------- Images ----------

def save_image(image, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def load_image(path):
    return Image.open(path)


# ---------- Pano_id ----------

def save_pano_id(pano_id, filepath=PANO_IDS_FILE):
    if not pano_id:
        return

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as file:
        file.write(f"{pano_id}\n")


# ---------- Location-based dataset structure ----------

def get_next_location_id(locations_root: str) -> str:
    """Returns next location id as zero-padded folder name, e.g. '000001'."""
    root = Path(locations_root)
    root.mkdir(parents=True, exist_ok=True)

    existing_ids = []
    for child in root.iterdir():
        if child.is_dir() and child.name.isdigit():
            existing_ids.append(int(child.name))

    next_id = 1 if not existing_ids else max(existing_ids) + 1
    return f"{next_id:06d}"


def create_location_folder(locations_root: str, location_id: str = None) -> Path:
    """Creates location folder with cubemap subfolder and returns the folder path."""
    if location_id is None:
        location_id = get_next_location_id(locations_root)

    location_dir = Path(locations_root) / location_id
    cubemap_dir = location_dir / "cubemap"

    cubemap_dir.mkdir(parents=True, exist_ok=True)
    return location_dir


def save_location_metadata(locations_root: str, location_id: str, metadata: dict) -> str:
    """Saves metadata.json inside one location folder."""
    location_dir = create_location_folder(locations_root, location_id)
    metadata_path = location_dir / "metadata.json"
    save_json(metadata, str(metadata_path))
    return str(metadata_path)


def save_location_cubemap(
    locations_root: str,
    location_id: str,
    cubemap_images: Dict[str, Image.Image],
    image_ext: str = "jpg",
):
    """
    Saves cubemap faces inside:
      <locations_root>/<location_id>/cubemap/{front,back,left,right,up,down}.<ext>

    Required face names: front, back, left, right, up, down
    """
    missing_faces = [face for face in CUBEMAP_FACES if face not in cubemap_images]
    if missing_faces:
        raise ValueError(f"Missing cubemap faces: {missing_faces}")

    location_dir = create_location_folder(locations_root, location_id)
    cubemap_dir = location_dir / "cubemap"

    for face in CUBEMAP_FACES:
        image_path = cubemap_dir / f"{face}.{image_ext}"
        cubemap_images[face].save(image_path)


def save_location_record(
    locations_root: str,
    metadata: dict,
    cubemap_images: Dict[str, Image.Image],
    location_id: str = None,
    image_ext: str = "jpg",
) -> str:
    """Creates one location folder and saves both metadata + cubemap faces."""
    if location_id is None:
        location_id = get_next_location_id(locations_root)

    create_location_folder(locations_root, location_id)
    save_location_metadata(locations_root, location_id, metadata)
    save_location_cubemap(locations_root, location_id, cubemap_images, image_ext=image_ext)
    return location_id
