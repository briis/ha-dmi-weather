"""Link to the location's page on dmi.dk (used as the device's "Visit" link).

dmi.dk addresses locations by GeoNames ID, e.g.
https://www.dmi.dk/lokation/show/DK/2620997/Gundsømagle - not by coordinates.
We ship a small list of places (GeoNames, CC BY 4.0) and pick the nearest one.
No requests are made to DMI or GeoNames.
"""

from __future__ import annotations

from functools import cache
import json
import math
from pathlib import Path
from urllib.parse import quote

DMI_DK_URL = "https://www.dmi.dk"
DMI_DK_PREFIX = "https://www.dmi.dk/"

# Further away than this, the nearest place is not "your" place: link to dmi.dk itself.
MAX_DISTANCE_KM = 30.0

_PLACES_FILE = Path(__file__).parent / "places.json"


@cache
def _places() -> list[list]:
    """[geonameid, name, lat, lon, country] for DK, FO and GL. Blocking file read."""
    with _PLACES_FILE.open(encoding="utf-8") as file:
        return json.load(file)["places"]


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Equirectangular approximation - accurate enough at these distances."""
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371.0 * math.hypot(x, y)


def nearest_place(latitude: float, longitude: float) -> tuple[int, str, str, float] | None:
    """(geonameid, name, country, distance_km) of the nearest place, or None if too far."""
    best = min(
        _places(),
        key=lambda p: _distance_km(latitude, longitude, p[2], p[3]),
    )
    distance = _distance_km(latitude, longitude, best[2], best[3])
    if distance > MAX_DISTANCE_KM:
        return None
    return best[0], best[1], best[4], distance


def suggest_dmi_url(latitude: float, longitude: float) -> str:
    """dmi.dk page for the nearest place, or dmi.dk's front page. Blocking (file read)."""
    place = nearest_place(latitude, longitude)
    if place is None:
        return DMI_DK_URL
    geoname_id, name, country, _ = place
    return f"{DMI_DK_URL}/lokation/show/{country}/{geoname_id}/{quote(name.replace(' ', '_'))}"


def is_dmi_url(url: str) -> bool:
    """True for an address on dmi.dk."""
    return url.strip().startswith(DMI_DK_PREFIX) or url.strip() == DMI_DK_URL
