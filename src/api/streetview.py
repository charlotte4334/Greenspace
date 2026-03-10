from io import BytesIO
import time

import requests
from PIL import Image

from config.settings import API_KEY, PANO_IDS_FILE


def api_streetview_metadata(lat, lon):
    """
    Returns Street View metadata for a given location.
    Filters out duplicates and non-summer months (Apr - Sep).
    """

    metadata_url = (
        "https://maps.googleapis.com/maps/api/streetview/metadata"
        f"?location={lat},{lon}&key={API_KEY}"
    )

    response = requests.get(metadata_url, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        return None, "not found"

    pano_id = data.get("pano_id")
    date = data.get("date")


    if check_duplicate(pano_id):
        status = "duplicate"
        return None, status

    if date and "-" in date:
        month = int(date.split("-")[1])
        if month < 4 or month > 9:
            status = "not summer"
            return None, status
    status = "ok"

    return data, status


def api_streetview_panorama(pano_id, size="640x640", fov=90):
    """
    Fetches six cubemap faces for a given panorama id and returns them as PIL images.

    Returns:
        dict with keys: front, back, left, right, up, down
    """
    if not pano_id:
        raise ValueError("pano_id is required")

    face_params = {
        "front": {"heading": 0, "pitch": 0},
        "right": {"heading": 90, "pitch": 0},
        "back": {"heading": 180, "pitch": 0},
        "left": {"heading": 270, "pitch": 0},
        "up": {"heading": 0, "pitch": 90},
        "down": {"heading": 0, "pitch": -90},
    }

    cubemap = {}

    for face, params in face_params.items():
        image_url = (
            "https://maps.googleapis.com/maps/api/streetview"
            f"?size={size}&pano={pano_id}&fov={fov}"
            f"&heading={params['heading']}&pitch={params['pitch']}"
            f"&key={API_KEY}"
        )

        response = _request_with_retries(image_url, timeout=60, retries=4, base_delay=1.0)
        cubemap[face] = Image.open(BytesIO(response.content)).convert("RGB")

    return cubemap


def _request_with_retries(url, timeout=60, retries=4, base_delay=1.0):
    """HTTP GET with retry/backoff for transient Street View API failures."""
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)

            # retry on transient server-side or quota throttling errors
            if response.status_code >= 500 or response.status_code == 429:
                raise requests.HTTPError(
                    f"HTTP {response.status_code} for URL: {url}", response=response
                )

            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            is_last_attempt = attempt == retries - 1
            if is_last_attempt:
                break

            delay = base_delay * (2 ** attempt)
            time.sleep(delay)

    raise RuntimeError(f"Street View request failed after {retries} attempts: {last_error}")


def check_duplicate(pano_id):
    """Returns True if pano_id already exists in the dataset."""
    if not pano_id:
        return False

    try:
        with open(PANO_IDS_FILE, "r", encoding="utf-8") as file:
            existing_pano_ids = set(line.strip() for line in file)
    except FileNotFoundError:
        return False

    return pano_id in existing_pano_ids
