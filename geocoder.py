"""
geocoder.py - Global Geocoding Engine for Countries, States, and Cities
Uses geopy.geocoders.Nominatim to resolve global location queries
into exact spatial bounding box coordinates (xmin, ymin, xmax, ymax).
"""

import logging
from typing import Dict, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError, GeocoderUnavailable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "gmb_global_directory_crawler_v2.0 (contact: info@directory-crawler.local)"


def get_geolocator(user_agent: str = DEFAULT_USER_AGENT, timeout: int = 10) -> Nominatim:
    """Initializes and returns a Nominatim geocoder instance."""
    return Nominatim(user_agent=user_agent, timeout=timeout)


def apply_bounding_box_buffer(
    bbox: Tuple[float, float, float, float],
    buffer_ratio: float = 0.0
) -> Tuple[float, float, float, float]:
    """
    Expands a bounding box by buffer_ratio (e.g. 0.20 = 20% expansion)
    to capture the surrounding metropolitan area / suburbs.
    Clamps coordinates to valid geographic limits [-180, 180] and [-90, 90].
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

    return (new_xmin, new_ymin, new_xmax, new_ymax)


def get_bounding_box(
    location_query: str,
    buffer_ratio: float = 0.0,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 10,
    max_retries: int = 2
) -> Tuple[float, float, float, float]:
    """
    Resolves any global location query (e.g. 'Austin, Texas, United States'
    or 'Toronto, Ontario, Canada') to bounding box coordinates: (xmin, ymin, xmax, ymax).

    Parameters:
        location_query (str): Comma-separated location query.
        buffer_ratio (float): Fraction to expand boundary (e.g. 0.20 for 20% surrounding area).
        user_agent (str): Custom user-agent.
        timeout (int): Request timeout in seconds.
        max_retries (int): Number of retry attempts.

    Returns:
        Tuple[float, float, float, float]:
            xmin (west lon), ymin (south lat), xmax (east lon), ymax (north lat).
    """
    if not location_query or not location_query.strip():
        raise ValueError("Location query must not be empty.")

    geolocator = get_geolocator(user_agent=user_agent, timeout=timeout)
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Geocoding '{location_query}' (Attempt {attempt}/{max_retries})...")
            # Global lookup without country restrictions
            location = geolocator.geocode(
                query=location_query.strip(),
                addressdetails=True,
                exactly_one=True
            )

            # Fallback attempt if comma format was too restrictive
            if location is None and "," in location_query:
                # Try with city and country parts
                parts = [p.strip() for p in location_query.split(",") if p.strip()]
                if len(parts) >= 2:
                    simplified = f"{parts[0]}, {parts[-1]}"
                    logger.info(f"Retrying with simplified query: '{simplified}'")
                    location = geolocator.geocode(
                        query=simplified,
                        addressdetails=True,
                        exactly_one=True
                    )

            if location is None:
                raise ValueError(
                    f"Could not find location coordinates for '{location_query}'. "
                    "Please verify spelling or select a neighboring city."
                )

            raw = getattr(location, "raw", {})
            bbox = raw.get("boundingbox")

            if not bbox or len(bbox) < 4:
                # If bounding box is missing, construct a default 5km bounding box around point
                lat, lon = float(location.latitude), float(location.longitude)
                ymin, ymax, xmin, xmax = lat - 0.05, lat + 0.05, lon - 0.05, lon + 0.05
            else:
                # Nominatim returns: [south_lat, north_lat, west_lon, east_lon]
                ymin = float(bbox[0])
                ymax = float(bbox[1])
                xmin = float(bbox[2])
                xmax = float(bbox[3])

            # Apply buffer if surrounding area requested
            final_bbox = apply_bounding_box_buffer((xmin, ymin, xmax, ymax), buffer_ratio)

            logger.info(
                f"Resolved '{location_query}' -> {location.address} | "
                f"Final BBox: (xmin={final_bbox[0]:.4f}, ymin={final_bbox[1]:.4f}, "
                f"xmax={final_bbox[2]:.4f}, ymax={final_bbox[3]:.4f})"
            )
            return final_bbox

        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning(f"Geocoding timeout on attempt {attempt}: {e}")
            last_exception = e
        except GeocoderServiceError as e:
            logger.error(f"Geocoding service error: {e}")
            raise

    raise GeocoderServiceError(
        f"Geocoding service timed out after {max_retries} attempts for '{location_query}': {last_exception}"
    )


def geocode_location_details(
    location_query: str,
    buffer_ratio: float = 0.0,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = 10
) -> Dict[str, any]:
    """
    Returns complete metadata for a global location:
    display address, coordinates, and calculated bounding box.
    """
    geolocator = get_geolocator(user_agent=user_agent, timeout=timeout)
    location = geolocator.geocode(
        query=location_query.strip(),
        addressdetails=True,
        exactly_one=True
    )

    if not location and "," in location_query:
        parts = [p.strip() for p in location_query.split(",") if p.strip()]
        if len(parts) >= 2:
            location = geolocator.geocode(
                query=f"{parts[0]}, {parts[-1]}",
                addressdetails=True,
                exactly_one=True
            )

    if not location:
        raise ValueError(f"Could not resolve location: '{location_query}'")

    raw = getattr(location, "raw", {})
    bbox = raw.get("boundingbox", [])
    if len(bbox) >= 4:
        ymin, ymax, xmin, xmax = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    else:
        lat, lon = float(location.latitude), float(location.longitude)
        xmin, ymin, xmax, ymax = lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05

    final_bbox = apply_bounding_box_buffer((xmin, ymin, xmax, ymax), buffer_ratio)

    return {
        "query": location_query,
        "display_name": location.address,
        "latitude": float(location.latitude),
        "longitude": float(location.longitude),
        "bounding_box": final_bbox,
        "xmin": final_bbox[0],
        "ymin": final_bbox[1],
        "xmax": final_bbox[2],
        "ymax": final_bbox[3],
        "raw": raw
    }


if __name__ == "__main__":
    test_locs = [
        ("Austin, Texas, United States", 0.0),
        ("Austin, Texas, United States", 0.20),
        ("Toronto, Ontario, Canada", 0.0),
        ("London, England, United Kingdom", 0.0)
    ]
    for loc_name, buf in test_locs:
        box = get_bounding_box(loc_name, buffer_ratio=buf)
        print(f"'{loc_name}' (buffer={buf}) -> BBox: {box}")
