import urllib.parse
from typing import Tuple

class MapsTool:
    """
    Handles Google Maps query URL formulation, directions mapping, 
    and path links based on lat/lon coordinates.
    """
    def __init__(self):
        pass

    def get_maps_url(self, name: str, coords: Tuple[float, float]) -> str:
        """
        Generates a Google Maps search URL which drops a pin at coords and displays the place name.
        """
        lat, lon = coords
        # Searching for "{Name} lat,lon" drops a pin at that precise spot
        query_str = f"{name} {lat},{lon}"
        encoded_query = urllib.parse.quote_plus(query_str)
        return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

    def get_directions_url(self, origin_coords: Tuple[float, float], dest_coords: Tuple[float, float]) -> str:
        """
        Generates a Google Maps directions URL from origin coordinates to destination coordinates.
        """
        orig_lat, orig_lon = origin_coords
        dest_lat, dest_lon = dest_coords
        return f"https://www.google.com/maps/dir/?api=1&origin={orig_lat},{orig_lon}&destination={dest_lat},{dest_lon}&travelmode=driving"
