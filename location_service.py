"""
location_service.py - Global Administrative Hierarchy Engine
Provides lightning-fast cascading Country -> State/Region -> City lookups
using geonamescache and bundled ISO administrative region mappings.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import geonamescache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for bundled data
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
ADMIN1_CODES_PATH = os.path.join(DATA_DIR, "admin1_codes.json")
CATEGORIES_PATH = os.path.join(DATA_DIR, "overture_categories.json")


class LocationService:
    """
    Singleton service handling global country, state/region, and city
    cascading hierarchies with in-memory caching.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocationService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info("Initializing LocationService...")
        self.gc = geonamescache.GeonamesCache()
        
        # Load country data
        countries_dict = self.gc.get_countries()
        self.country_name_to_iso: Dict[str, str] = {
            v["name"]: v["iso"] for v in countries_dict.values() if v.get("name") and v.get("iso")
        }
        self.iso_to_country_name: Dict[str, str] = {
            v: k for k, v in self.country_name_to_iso.items()
        }
        
        # Alphabetically sorted country names, with United States prioritized
        raw_countries = sorted(list(self.country_name_to_iso.keys()))
        if "United States" in raw_countries:
            raw_countries.remove("United States")
            self.sorted_countries = ["United States"] + raw_countries
        else:
            self.sorted_countries = raw_countries

        # Load admin1 code mappings (e.g., "US.TX" -> "Texas", "CA.02" -> "British Columbia")
        self.admin1_map: Dict[str, str] = {}
        if os.path.exists(ADMIN1_CODES_PATH):
            try:
                with open(ADMIN1_CODES_PATH, "r", encoding="utf-8") as f:
                    self.admin1_map = json.load(f)
                logger.info(f"Loaded {len(self.admin1_map)} admin1 subdivision mappings.")
            except Exception as e:
                logger.warning(f"Could not load admin1_codes.json: {e}")

        # Cache all cities from geonamescache
        self.cities = self.gc.get_cities()
        logger.info(f"Loaded {len(self.cities)} global cities (pop > 15k).")

        # Load complete Overture categories taxonomy
        self.categories: List[str] = []
        if os.path.exists(CATEGORIES_PATH):
            try:
                with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                    self.categories = json.load(f)
                logger.info(f"Loaded {len(self.categories)} official Overture categories.")
            except Exception as e:
                logger.warning(f"Could not load overture_categories.json: {e}")

    def get_countries(self) -> List[str]:
        """Returns sorted list of global country names."""
        return self.sorted_countries

    def get_country_iso(self, country_name: str) -> Optional[str]:
        """Returns the 2-letter ISO code for a country."""
        return self.country_name_to_iso.get(country_name)

    def get_states_for_country(self, country_name: str) -> Tuple[List[str], Dict[str, str]]:
        """
        Returns a sorted list of human-readable state/province/region names
        and a mapping of {state_name: admin1_code} for the given country.
        """
        iso = self.get_country_iso(country_name)
        if not iso:
            return [], {}

        # Collect unique admin1 codes from cities belonging to this country
        admin_codes = set()
        for city in self.cities.values():
            if city.get("countrycode") == iso:
                acode = city.get("admin1code")
                if acode:
                    admin_codes.add(acode)

        state_names = []
        state_to_code: Dict[str, str] = {}

        for code in admin_codes:
            lookup_key = f"{iso}.{code}"
            readable_name = self.admin1_map.get(lookup_key)
            if not readable_name:
                # If code is alphanumeric (e.g., 'ENG', 'TX'), use it as fallback
                readable_name = code
            state_names.append(readable_name)
            state_to_code[readable_name] = code

        # If no admin subdivisions found in cities, check admin1_map directly for this ISO
        if not state_names:
            prefix = f"{iso}."
            for k, v in self.admin1_map.items():
                if k.startswith(prefix):
                    code = k[len(prefix):]
                    state_names.append(v)
                    state_to_code[v] = code

        sorted_states = sorted(list(set(state_names)))
        return sorted_states, state_to_code

    def get_cities_for_state(
        self,
        country_name: str,
        state_name: str,
        state_to_code: Dict[str, str]
    ) -> List[str]:
        """
        Returns a sorted list of city names for the specified country and state.
        """
        iso = self.get_country_iso(country_name)
        if not iso:
            return []

        admin_code = state_to_code.get(state_name)

        matched_cities = set()
        for city in self.cities.values():
            if city.get("countrycode") == iso:
                if admin_code is None or city.get("admin1code") == admin_code:
                    matched_cities.add(city["name"])

        return sorted(list(matched_cities))

    def get_city_details(
        self,
        city_name: str,
        country_name: Optional[str] = None,
        state_name: Optional[str] = None
    ) -> Optional[Dict[str, any]]:
        """
        Retrieves offline city coordinates, population, and metadata in 0ms.
        Bypasses external geocoding APIs entirely.
        """
        iso = self.get_country_iso(country_name) if country_name else None
        c_name_clean = city_name.strip().lower()

        # Exact match first
        matches = []
        for city in self.cities.values():
            if iso and city.get("countrycode") != iso:
                continue
            if city.get("name", "").lower() == c_name_clean:
                matches.append(city)

        # Fallback to substring matching if no exact match
        if not matches:
            for city in self.cities.values():
                if iso and city.get("countrycode") != iso:
                    continue
                if c_name_clean in city.get("name", "").lower():
                    matches.append(city)

        if matches:
            best = max(matches, key=lambda x: x.get("population", 0))
            return {
                "name": best.get("name"),
                "latitude": float(best.get("latitude")),
                "longitude": float(best.get("longitude")),
                "population": int(best.get("population", 50000)),
                "countrycode": best.get("countrycode"),
                "admin1code": best.get("admin1code")
            }
        return None

    def get_all_categories(self) -> List[str]:
        """Returns the complete list of 2,100+ Overture categories."""
        return self.categories

    @staticmethod
    def format_location_query(city: str, state: Optional[str], country: str) -> str:
        """
        Builds a clean, comma-separated geocoding query string:
        e.g., 'Austin, Texas, United States' or 'London, England, United Kingdom'.
        """
        parts = []
        if city and city.strip():
            parts.append(city.strip())
        if state and state.strip() and state.strip() != "All Regions":
            parts.append(state.strip())
        if country and country.strip():
            parts.append(country.strip())
        return ", ".join(parts)


# Module-level helper instances
_service = None


def get_location_service() -> LocationService:
    """Returns singleton LocationService instance."""
    global _service
    if _service is None:
        _service = LocationService()
    return _service


if __name__ == "__main__":
    svc = get_location_service()
    countries = svc.get_countries()
    print(f"Total countries: {len(countries)}. Top 5: {countries[:5]}")
    
    us_states, us_map = svc.get_states_for_country("United States")
    print(f"US States ({len(us_states)}): {us_states[:5]}")
    
    tx_cities = svc.get_cities_for_state("United States", "Texas", us_map)
    print(f"Texas Cities ({len(tx_cities)}): {tx_cities[:5]}")
    
    cats = svc.get_all_categories()
    print(f"Total Overture Categories: {len(cats)}. Sample: {cats[:5]}")
