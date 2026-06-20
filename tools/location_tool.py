import re
from typing import Dict, List, Any, Tuple

class LocationTool:
    """
    Parses emergency queries for locations and simulates geocoding and local search.
    Provides verified mock data for major Indian cities (Mumbai, Pune, Delhi)
    including hospitals, fire stations, police stations, and disaster shelters.
    """
    def __init__(self):
        # Database of verified emergency locations
        self.location_db: Dict[str, Dict[str, Any]] = {
            "mumbai": {
                "coords": (19.0760, 72.8777),
                "hospitals": [
                    {"name": "KEM Hospital", "address": "Acharya Donde Marg, Parel, Mumbai", "phone": "+91-22-2410-7000", "status": "OPERATIONAL", "distance_km": 1.2, "verified_at": "2026-06-20"},
                    {"name": "Lilavati Hospital & Research Centre", "address": "A.S. Dixit Road, Bandra West, Mumbai", "phone": "+91-22-2675-1000", "status": "OPERATIONAL", "distance_km": 3.5, "verified_at": "2026-06-20"},
                    {"name": "Fortis Hospital Mulund", "address": "Mulund Goregaon Link Road, Mumbai", "phone": "+91-22-6799-4100", "status": "OPERATIONAL", "distance_km": 8.0, "verified_at": "2026-06-19"}
                ],
                "fire_stations": [
                    {"name": "Byculla Fire Station", "address": "Babasaheb Ambedkar Road, Byculla, Mumbai", "phone": "+91-22-2308-5991", "status": "OPERATIONAL", "distance_km": 2.1, "verified_at": "2026-06-20"},
                    {"name": "Bandra Fire Station", "address": "S.V. Road, Bandra West, Mumbai", "phone": "+91-22-2642-2222", "status": "OPERATIONAL", "distance_km": 4.0, "verified_at": "2026-06-20"}
                ],
                "police_stations": [
                    {"name": "Mumbai Police Head Office", "address": "Crawford Market, Fort, Mumbai", "phone": "+91-22-2262-0111", "status": "OPERATIONAL", "distance_km": 5.2, "verified_at": "2026-06-20"},
                    {"name": "Bandra Police Station", "address": "Hill Road, Bandra West, Mumbai", "phone": "+91-22-2642-2779", "status": "OPERATIONAL", "distance_km": 3.8, "verified_at": "2026-06-20"}
                ],
                "shelters": [
                    {"name": "Dharavi Community Relief Shelter", "address": "Sector 3, Dharavi, Mumbai", "phone": "+91-22-2407-1234", "status": "OPEN", "capacity": "500 beds", "distance_km": 2.5, "verified_at": "2026-06-20"},
                    {"name": "Chembur Sports Complex Shelter", "address": "St. Sebastian Road, Chembur, Mumbai", "phone": "+91-22-2522-5678", "status": "OPEN", "capacity": "300 beds", "distance_km": 6.7, "verified_at": "2026-06-20"}
                ]
            },
            "pune": {
                "coords": (18.5204, 73.8567),
                "hospitals": [
                    {"name": "Ruby Hall Clinic", "address": "Alibag Road, Pune", "phone": "+91-20-6645-5100", "status": "OPERATIONAL", "distance_km": 1.5, "verified_at": "2026-06-20"},
                    {"name": "KEM Hospital Pune", "address": "Rasta Peth, Pune", "phone": "+91-20-6603-7300", "status": "OPERATIONAL", "distance_km": 2.2, "verified_at": "2026-06-20"}
                ],
                "fire_stations": [
                    {"name": "Central Fire Station Pune", "address": "Mahatma Phule Peth, Pune", "phone": "+91-20-2645-1700", "status": "OPERATIONAL", "distance_km": 0.8, "verified_at": "2026-06-20"}
                ],
                "police_stations": [
                    {"name": "Shivajinagar Police Station", "address": "Shivajinagar, Pune", "phone": "+91-20-2550-1122", "status": "OPERATIONAL", "distance_km": 1.1, "verified_at": "2026-06-20"}
                ],
                "shelters": [
                    {"name": "Shivajinagar Relief Camp", "address": "Sports Ground, Shivajinagar, Pune", "phone": "+91-20-2550-3456", "status": "OPEN", "capacity": "400 beds", "distance_km": 1.3, "verified_at": "2026-06-20"}
                ]
            },
            "delhi": {
                "coords": (28.6139, 77.2090),
                "hospitals": [
                    {"name": "AIIMS New Delhi", "address": "Ansari Nagar, New Delhi", "phone": "+91-11-2658-8500", "status": "OPERATIONAL", "distance_km": 2.5, "verified_at": "2026-06-20"},
                    {"name": "Ram Manohar Lohia Hospital", "address": "Baba Kharak Singh Marg, New Delhi", "phone": "+91-11-2336-5525", "status": "OPERATIONAL", "distance_km": 1.8, "verified_at": "2026-06-20"}
                ],
                "fire_stations": [
                    {"name": "Connaught Place Fire Station", "address": "Outer Circle, Connaught Place, New Delhi", "phone": "+91-11-2341-2222", "status": "OPERATIONAL", "distance_km": 0.5, "verified_at": "2026-06-20"}
                ],
                "police_stations": [
                    {"name": "Parliament Street Police Station", "address": "Parliament Street, New Delhi", "phone": "+91-11-2336-1100", "status": "OPERATIONAL", "distance_km": 1.0, "verified_at": "2026-06-20"}
                ],
                "shelters": [
                    {"name": "NDMC Community Hall Shelter", "address": "Chanakyapuri, New Delhi", "phone": "+91-11-2411-9988", "status": "OPEN", "capacity": "600 beds", "distance_km": 3.1, "verified_at": "2026-06-20"}
                ]
            }
        }

    def parse_location(self, text: str) -> str:
        """
        Extracts known cities from query text.
        Defaults to 'mumbai' if no known city matches.
        """
        text_lower = text.lower()
        if "pune" in text_lower:
            return "pune"
        if "delhi" in text_lower or "new delhi" in text_lower:
            return "delhi"
        return "mumbai"  # Default fallback

    def geocode(self, location_name: str) -> Tuple[float, float]:
        """Returns mock coordinates for known locations."""
        key = self.parse_location(location_name)
        return self.location_db[key]["coords"]

    def search_resources(self, location_name: str, category: str) -> List[Dict[str, Any]]:
        """
        Searches resources matching the emergency category near the geocoded location.
        """
        city = self.parse_location(location_name)
        city_data = self.location_db[city]
        
        cat_lower = category.lower()
        resources = []
        
        if "medical" in cat_lower or "injured" in cat_lower or "health" in cat_lower or "hospital" in cat_lower:
            resources.extend(city_data["hospitals"])
        elif "fire" in cat_lower or "explosion" in cat_lower:
            resources.extend(city_data["fire_stations"])
            resources.extend(city_data["hospitals"])  # hospital as backup for burns
        elif "safety" in cat_lower or "crime" in cat_lower or "police" in cat_lower or "rescue" in cat_lower:
            resources.extend(city_data["police_stations"])
            resources.extend(city_data["shelters"])
        else:
            # General query gets shelters and general contacts
            resources.extend(city_data["shelters"])
            resources.extend(city_data["hospitals"])
            
        return resources
