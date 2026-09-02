"""
geocoder.py - Robust Global Geocoding Engine
Resolves global locations to precise spatial bounding boxes (xmin, ymin, xmax, ymax).
Prioritizes offline GeoNamesCache for 0ms, zero-rate-limit lookups,
with Photon and Nominatim fallbacks to ensure full reliability on cloud environments.
"""

import json
import logging
import math
from typing import Dict, Optional, Tuple
import urllib.parse
import urllib.request
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable

# Import location service for offline zero-latency city lookups
from location_service import get_location_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "gmb_global_directory_crawler_v2.0 (contact: info@directory-crawler.local)"


def get_geolocator(user_agent: str = DEFAULT_USER_AGENT, timeout: int = 10) -> Nominatim:
    """Initializes and returns a Nominatim geocoder instance."""
    return Nominatim(user_agent=user_agent, timeout=timeout)


def bbox_from_point(
    lat: float,
    lon: float,
    pop: int = 100000,
    buffer_ratio: float = 0.0
) -> Tuple[float, float, float, float]:
    """
    Constructs a bounding box around a lat/lon center point scaled to the city's population/size.
    Clamps coordinates to valid geographic limits [-180, 180] and [-90, 90].
    """
    if pop > 2000000:
        radius_km = 16.0
    elif pop > 1000000:
        radius_km = 13.0
    elif pop > 300000:
        radius_km = 9.0
    elif pop > 50000:
        radius_km = 6.5
    else:
        radius_km = 4.5

    radius_km *= (1.0 + buffer_ratio)

    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.15, math.cos(math.radians(lat))))

    xmin = max(-180.0, lon - dlon)
    xmax = min(180.0, lon + dlon)
    ymin = max(-90.0, lat - dlat)
    ymax = min(90.0, lat + dlat)

    return (round(xmin, 4), round(ymin, 4), round(xmax, 4), round(ymax, 4))


def apply_bounding_box_buffer(
    bbox: Tuple[float, float, float, float],
    buffer_ratio: float = 0.0
) -> Tuple[float, float, float, float]:
    """
    Expands a bounding box by buffer_ratio (e.g. 0.20 = 20% expansion)
    to capture the surrounding metropolitan area / suburbs.
    """
    if buffer_ratio <= 0.0:
        return bbox

    xmin, ymin, xmax, ymax = bbox
    dx = (xmax - xmin) * buffer_ratio
    dy = (ymax - ymin) * buffer_ratio

    new_xmin = max(-180.0, xmin - dx)
    new_xmax = min(180.0, xmax + dx)
    new_ymin = max(-90.0, ymin - dy)
    new_ymax = min(90.0, ymax + dy)

    return (round(new_xmin, 4), round(new_ymin, 4), round(new_xmax, 4), round(new_ymax, 4))


def _geocode_via_photon(query: str) -> Optional[Dict[str, any]]:
    """
    Fallback geocoder using Photon (OSM-based).
    Free, fast, and does not block shared cloud IPs (unlike Nominatim).
    """
    try:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(query)}&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "GMB-Crawler-App/2.0 (Mozilla/5.0 compatible)"}
        )
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                features = data.get("features", [])
                if features:
                    feat = features[0]
                    coords = feat.get("geometry", {}).get("coordinates", [])
                    props = feat.get("properties", {})
                    if len(coords) >= 2:
                        lon, lat = float(coords[0]), float(coords[1])
                        name = props.get("name") or props.get("city") or query
                        extent = props.get("extent")  # [min_lon, max_lat, max_lon, min_lat]
                        return {
                            "name": name,
                            "lat": lat,
                            "lon": lon,
                            "extent": extent,
                            "properties": props
                        }
    except Exception as e:
        logger.warning(f"Photon geocoder lookup notice: {e}")
    return None


def geocode_location_details(
    location_query: str,
    buffer_ratio: float = 0.0,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 10
) -> Dict[str, any]:
    """
    Returns complete metadata for a global location:
    display address, coordinates, and calculated bounding box.
    Uses a 3-tier architecture:
      1. Offline GeoNamesCache (0ms, 0 HTTP calls, immune to 429 rate limits).
      2. Photon OSM API (Cloud-friendly fallback).
      3. Nominatim OSM API (with graceful error handling).
    """
    if not location_query or not location_query.strip():
        raise ValueError("Location query must not be empty.")

    clean_query = location_query.strip()
    parts = [p.strip() for p in clean_query.split(",") if p.strip()]

    # ---------------- TIER 1: OFFLINE GEONAMESCACHE (0ms, Zero Rate Limits) ----------------
    if parts:
        city_candidate = parts[0]
        country_candidate = parts[-1] if len(parts) >= 2 else None
        state_candidate = parts[1] if len(parts) >= 3 else None

        loc_svc = get_location_service()
        city_info = loc_svc.get_city_details(
            city_name=city_candidate,
            country_name=country_candidate,
            state_name=state_candidate
        )

        if city_info:
            lat = city_info["latitude"]
            lon = city_info["longitude"]
            pop = city_info.get("population", 100000)
            final_bbox = bbox_from_point(lat, lon, pop=pop, buffer_ratio=buffer_ratio)
            display_str = f"{city_info['name']}, {country_candidate or city_info.get('countrycode', '')}"

            logger.info(
                f"Resolved via offline GeoNamesCache: '{clean_query}' -> {display_str} | "
                f"BBox: {final_bbox}"
            )

            return {
                "query": clean_query,
                "display_name": display_str,
                "latitude": lat,
                "longitude": lon,
                "bounding_box": final_bbox,
                "xmin": final_bbox[0],
                "ymin": final_bbox[1],
                "xmax": final_bbox[2],
                "ymax": final_bbox[3],
                "source": "offline_geonamescache"
            }

    # ---------------- TIER 2: PHOTON OSM API (Cloud IP Friendly) ----------------
    photon_res = _geocode_via_photon(clean_query)
    if photon_res:
        lat = photon_res["lat"]
        lon = photon_res["lon"]
        extent = photon_res.get("extent")

        if extent and len(extent) >= 4:
            # extent: [min_lon, max_lat, max_lon, min_lat]
            raw_bbox = (float(extent[0]), float(extent[3]), float(extent[2]), float(extent[1]))
            final_bbox = apply_bounding_box_buffer(raw_bbox, buffer_ratio)
        else:
            final_bbox = bbox_from_point(lat, lon, pop=200000, buffer_ratio=buffer_ratio)

        logger.info(f"Resolved via Photon: '{clean_query}' -> {photon_res['name']} | BBox: {final_bbox}")
        return {
            "query": clean_query,
            "display_name": f"{photon_res['name']}, {clean_query}",
            "latitude": lat,
            "longitude": lon,
            "bounding_box": final_bbox,
            "xmin": final_bbox[0],
            "ymin": final_bbox[1],
            "xmax": final_bbox[2],
            "ymax": final_bbox[3],
            "source": "photon_api"
        }

    # ---------------- TIER 3: NOMINATIM OSM API (Fallback with 429 Protection) ----------------
    try:
        geolocator = get_geolocator(user_agent=user_agent, timeout=timeout)
        location = geolocator.geocode(query=clean_query, addressdetails=True, exactly_one=True)

        if not location and len(parts) >= 2:
            simplified = f"{parts[0]}, {parts[-1]}"
            location = geolocator.geocode(query=simplified, addressdetails=True, exactly_one=True)

        if location:
            raw = getattr(location, "raw", {})
            bbox = raw.get("boundingbox", [])
            if len(bbox) >= 4:
                ymin, ymax, xmin, xmax = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                final_bbox = apply_bounding_box_buffer((xmin, ymin, xmax, ymax), buffer_ratio)
            else:
                lat, lon = float(location.latitude), float(location.longitude)
                final_bbox = bbox_from_point(lat, lon, pop=100000, buffer_ratio=buffer_ratio)

            return {
                "query": clean_query,
                "display_name": location.address,
                "latitude": float(location.latitude),
                "longitude": float(location.longitude),
                "bounding_box": final_bbox,
                "xmin": final_bbox[0],
                "ymin": final_bbox[1],
                "xmax": final_bbox[2],
                "ymax": final_bbox[3],
                "source": "nominatim_api"
            }
    except (GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable) as e:
        logger.warning(f"Nominatim encountered service notice ({e}).")

    raise ValueError(
        f"Could not resolve geographic boundaries for '{clean_query}'. "
        "Please select a neighboring city or verify spelling."
    )


def get_bounding_box(
    location_query: str,
    buffer_ratio: float = 0.0,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 10,
    max_retries: int = 2
) -> Tuple[float, float, float, float]:
    """Convenience wrapper returning only the 4-element bounding box tuple."""
    details = geocode_location_details(
        location_query=location_query,
        buffer_ratio=buffer_ratio,
        user_agent=user_agent,
        timeout=timeout
    )
    return details["bounding_box"]


if __name__ == "__main__":
    test_locs = [
        "Bhopal, Madhya Pradesh, India",
        "Austin, Texas, United States",
        "Toronto, Ontario, Canada",
        "London, England, United Kingdom",
        "Solon, Ohio, United States"
    ]
    for loc in test_locs:
        details = geocode_location_details(loc)
        print(f"'{loc}' -> {details['source']} | Lat/Lon: ({details['latitude']}, {details['longitude']}) | BBox: {details['bounding_box']}")
