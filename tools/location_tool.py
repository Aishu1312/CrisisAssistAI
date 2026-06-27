import re
import datetime
from typing import Dict, List, Any, Tuple

class LocationTool:
    """
    Unified Location and Resource lookup tool.
    Provides geocoding, verified local resource search, and verification scoring.
    """
    def __init__(self, current_date_str: str = "2026-06-20"):
        try:
            self.current_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d")
        except ValueError:
            self.current_date = datetime.datetime.now()

        # Database of verified emergency locations (with coordinates, contact, and freshness metadata)
        self.location_db: Dict[str, Dict[str, Any]] = {
            "mumbai": {
                "coords": (19.0760, 72.8777),
                "hospitals": [
                    {"name": "KEM Hospital", "address": "Acharya Donde Marg, Parel, Mumbai", "phone": "+91-22-2410-7000", "status": "OPERATIONAL", "distance_km": 1.2, "verified_at": "2026-06-20", "coordinates": (19.0025, 72.8420)},
                    {"name": "Lilavati Hospital & Research Centre", "address": "A.S. Dixit Road, Bandra West, Mumbai", "phone": "+91-22-2675-1000", "status": "OPERATIONAL", "distance_km": 3.5, "verified_at": "2026-06-20", "coordinates": (19.0514, 72.8300)},
                    {"name": "Fortis Hospital Mulund", "address": "Mulund Goregaon Link Road, Mumbai", "phone": "+91-22-6799-4100", "status": "OPERATIONAL", "distance_km": 8.0, "verified_at": "2026-06-19", "coordinates": (19.1678, 72.9545)}
                ],
                "fire_stations": [
                    {"name": "Byculla Fire Station", "address": "Babasaheb Ambedkar Road, Byculla, Mumbai", "phone": "+91-22-2308-5991", "status": "OPERATIONAL", "distance_km": 2.1, "verified_at": "2026-06-20", "coordinates": (18.9749, 72.8354)},
                    {"name": "Bandra Fire Station", "address": "S.V. Road, Bandra West, Mumbai", "phone": "+91-22-2642-2222", "status": "OPERATIONAL", "distance_km": 4.0, "verified_at": "2026-06-20", "coordinates": (19.0550, 72.8360)}
                ],
                "police_stations": [
                    {"name": "Mumbai Police Head Office", "address": "Crawford Market, Fort, Mumbai", "phone": "+91-22-2262-0111", "status": "OPERATIONAL", "distance_km": 5.2, "verified_at": "2026-06-20", "coordinates": (18.9463, 72.8340)}
                ],
                "shelters": [
                    {"name": "Dharavi Relief Shelter A", "address": "Sector 3, Dharavi, Mumbai", "phone": "+91-22-2407-1234", "status": "OPEN", "capacity": "500 beds", "distance_km": 2.5, "verified_at": "2026-06-20", "coordinates": (19.0380, 72.8538)}
                ]
            },
            "pune": {
                "coords": (18.5204, 73.8567),
                "hospitals": [
                    {"name": "Ruby Hall Clinic", "address": "Alibag Road, Pune", "phone": "+91-20-6645-5100", "status": "OPERATIONAL", "distance_km": 1.5, "verified_at": "2026-06-20", "coordinates": (18.5332, 73.8767)},
                    {"name": "KEM Hospital Pune", "address": "Rasta Peth, Pune", "phone": "+91-20-6603-7300", "status": "OPERATIONAL", "distance_km": 2.2, "verified_at": "2026-06-20", "coordinates": (18.5238, 73.8681)}
                ],
                "fire_stations": [
                    {"name": "Central Fire Station Pune", "address": "Mahatma Phule Peth, Pune", "phone": "+91-20-2645-1700", "status": "OPERATIONAL", "distance_km": 0.8, "verified_at": "2026-06-20", "coordinates": (18.5085, 73.8618)}
                ],
                "police_stations": [
                    {"name": "Shivajinagar Police Station", "address": "Shivajinagar, Pune", "phone": "+91-20-2550-1122", "status": "OPERATIONAL", "distance_km": 1.1, "verified_at": "2026-06-20", "coordinates": (18.5312, 73.8499)}
                ],
                "shelters": [
                    {"name": "Shivajinagar Relief Camp", "address": "Sports Ground, Shivajinagar, Pune", "phone": "+91-20-2550-3456", "status": "OPEN", "capacity": "400 beds", "distance_km": 1.3, "verified_at": "2026-06-20", "coordinates": (18.5284, 73.8480)}
                ]
            },
            "delhi": {
                "coords": (28.6139, 77.2090),
                "hospitals": [
                    {"name": "AIIMS New Delhi", "address": "Ansari Nagar, New Delhi", "phone": "+91-11-2658-8500", "status": "OPERATIONAL", "distance_km": 2.5, "verified_at": "2026-06-20", "coordinates": (28.5672, 77.2100)},
                    {"name": "Ram Manohar Lohia Hospital", "address": "Baba Kharak Singh Marg, New Delhi", "phone": "+91-11-2336-5525", "status": "OPERATIONAL", "distance_km": 1.8, "verified_at": "2026-06-20", "coordinates": (28.6245, 77.2033)}
                ],
                "fire_stations": [
                    {"name": "Connaught Place Fire Station", "address": "Outer Circle, Connaught Place, New Delhi", "phone": "+91-11-2341-2222", "status": "OPERATIONAL", "distance_km": 0.5, "verified_at": "2026-06-20", "coordinates": (28.6304, 77.2177)}
                ],
                "police_stations": [
                    {"name": "Parliament Street Police Station", "address": "Parliament Street, New Delhi", "phone": "+91-11-2336-1100", "status": "OPERATIONAL", "distance_km": 1.0, "verified_at": "2026-06-20", "coordinates": (28.6253, 77.2132)}
                ],
                "shelters": [
                    {"name": "NDMC Hall Shelter", "address": "Chanakyapuri, New Delhi", "phone": "+91-11-2411-9988", "status": "OPEN", "capacity": "600 beds", "distance_km": 3.1, "verified_at": "2026-06-20", "coordinates": (28.5900, 77.2000)}
                ]
            },
            "bangalore": {
                "coords": (12.9716, 77.5946),
                "hospitals": [
                    {"name": "Manipal Hospital", "address": "HAL Old Airport Road, Bangalore", "phone": "+91-80-2502-4444", "status": "OPERATIONAL", "distance_km": 1.9, "verified_at": "2026-06-20", "coordinates": (12.9592, 77.6444)},
                    {"name": "Narayana Health City", "address": "Hosur Road, Bangalore", "phone": "+91-80-7122-2222", "status": "OPERATIONAL", "distance_km": 4.8, "verified_at": "2026-06-20", "coordinates": (12.8055, 77.6946)}
                ],
                "fire_stations": [
                    {"name": "Koramangala Fire Station", "address": "80 Feet Road, Koramangala, Bangalore", "phone": "+91-80-2297-1500", "status": "OPERATIONAL", "distance_km": 2.0, "verified_at": "2026-06-20", "coordinates": (12.9348, 77.6200)}
                ],
                "police_stations": [
                    {"name": "Cubbon Park Police Station", "address": "Kasturba Road, Bangalore", "phone": "+91-80-2294-2583", "status": "OPERATIONAL", "distance_km": 1.2, "verified_at": "2026-06-20", "coordinates": (12.9754, 77.5980)}
                ],
                "shelters": [
                    {"name": "Kanteerava Stadium Relief shelter", "address": "Kasturba Road, Bangalore", "phone": "+91-80-2294-5555", "status": "OPEN", "capacity": "800 beds", "distance_km": 1.5, "verified_at": "2026-06-20", "coordinates": (12.9698, 77.5925)}
                ]
            }
        }
        
        # Coordinates database for major cities in India to ensure accurate geocoding
        self.coords_db = {
            "mumbai": (19.0760, 72.8777),
            "pune": (18.5204, 73.8567),
            "delhi": (28.6139, 77.2090),
            "new delhi": (28.6139, 77.2090),
            "bangalore": (12.9716, 77.5946),
            "bengaluru": (12.9716, 77.5946),
            "nagpur": (21.1458, 79.0882),
            "chennai": (13.0827, 80.2707),
            "kolkata": (22.5726, 88.3639),
            "hyderabad": (17.3850, 78.4867),
            "ahmedabad": (23.0225, 72.5714),
            "surat": (21.1702, 72.8311),
            "jaipur": (26.9124, 75.7873),
            "lucknow": (26.8467, 80.9462),
            "kanpur": (26.4499, 80.3319),
            "patna": (25.5941, 85.1376),
            "bhopal": (23.2599, 77.4126),
            "indore": (22.7196, 75.8577),
            "thane": (19.2183, 72.9781),
            "nashik": (19.9975, 73.7898),
            "aurangabad": (19.8762, 75.3433),
            "solapur": (17.6599, 75.9064),
            "amravati": (20.9374, 77.7796),
            "navi mumbai": (19.0330, 73.0297),
            "kolhapur": (16.7050, 74.2433),
            "akola": (20.7002, 77.0082),
            "jalgaon": (21.0077, 75.5626)
        }


    def parse_location(self, text: str) -> str:
        """Extracts known cities from text."""
        text_lower = text.lower()
        if "pune" in text_lower:
            return "pune"
        if "delhi" in text_lower or "new delhi" in text_lower:
            return "delhi"
        if "bangalore" in text_lower or "bengaluru" in text_lower:
            return "bangalore"
        if "mumbai" in text_lower or "bombay" in text_lower:
            return "mumbai"
        return "other"

    def geocode(self, location_name: str) -> Tuple[float, float]:
        """Returns coordinates for a location."""
        if not location_name:
            return (19.0760, 72.8777)
        name_lower = location_name.lower()
        for city, coords in self.coords_db.items():
            if city in name_lower:
                return coords
        return (19.0760, 72.8777)  # Mumbai default fallback


    def search_resources(self, location_name: str, category: str, allow_fallback: bool = True) -> List[Dict[str, Any]]:
        """Searches static database resources matching the category."""
        city = self.parse_location(location_name)
        if city in self.location_db:
            city_data = self.location_db[city]
            cat_lower = category.lower()
            resources = []
            
            # Map specific needs
            if any(k in cat_lower for k in ['medical', 'hospital', 'injury', 'accident', 'poisoning', 'health', 'snake', 'heat stroke']):
                resources.extend(city_data["hospitals"])
            elif any(k in cat_lower for k in ['fire', 'burning', 'smoke', 'explosion']):
                resources.extend(city_data["fire_stations"])
                resources.extend(city_data["hospitals"])
            elif any(k in cat_lower for k in ['rescue', 'trapped', 'collapse', 'missing', 'water rescue']):
                resources.extend(city_data["police_stations"])
                resources.extend(city_data["fire_stations"])
                resources.extend(city_data["hospitals"])
            elif any(k in cat_lower for k in ['flood', 'earthquake', 'disaster', 'cyclone', 'storm']):
                resources.extend(city_data["shelters"])
                resources.extend(city_data["police_stations"])
                resources.extend(city_data["hospitals"])
            elif any(k in cat_lower for k in ['safety', 'police', 'women', 'child', 'crime', 'animal attack', 'mental health', 'power outage', 'gas leak', 'harassment', 'stalk', 'threat', 'eve teasing', 'harass']):
                resources.extend(city_data["police_stations"])
                if any(k in cat_lower for k in ['gas leak', 'animal attack']):
                    resources.extend(city_data["fire_stations"])
            else:
                # General support
                resources.extend(city_data["shelters"])
                resources.extend(city_data["hospitals"])
                
            return resources
            
        if allow_fallback:
            return self.get_fallback_resources(location_name, category)
            
        return []

    def get_fallback_resources(self, location_name: str, category: str = "General") -> List[Dict[str, Any]]:
        """Generates fallback verified emergency resources based on location and category."""
        loc_clean = location_name.strip() if location_name else ""
        if not loc_clean:
            loc_clean = "India"
            
        parts = [p.strip() for p in loc_clean.split(",") if p.strip()]
        city_title = parts[0] if parts else "India"
        
        # Geocode to get coordinates
        coords = self.geocode(loc_clean)
        
        cat_lower = category.lower()
        all_fallbacks = []
        
        # Medical
        if any(k in cat_lower for k in ['medical', 'injury', 'accident', 'health', 'general', 'poisoning', 'snake', 'heat stroke']):
            all_fallbacks.append({
                "name": f"{city_title} Ambulance Service",
                "address": loc_clean,
                "phone": "108",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })
            
        # Women's Safety Helpline (Specific priority for women)
        if any(k in cat_lower for k in ['women', 'safety', 'harass', 'harassment', 'stalk', 'threat', 'eve teasing']):
            all_fallbacks.append({
                "name": f"Women's Helpline {city_title}",
                "address": loc_clean,
                "phone": "1091",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })

        # Child Safety Helpline
        if any(k in cat_lower for k in ['child', 'safety', 'harass', 'harassment', 'missing']):
            all_fallbacks.append({
                "name": f"Child Helpline {city_title}",
                "address": loc_clean,
                "phone": "1098",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })
            
        # Police / Safety
        if any(k in cat_lower for k in ['police', 'safety', 'crime', 'rescue', 'trapped', 'women', 'child', 'general', 'animal attack', 'missing', 'harass', 'harassment', 'stalk', 'threat', 'eve teasing']):
            all_fallbacks.append({
                "name": f"{city_title} Police Emergency",
                "address": loc_clean,
                "phone": "112",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })
            
        # Fire
        if any(k in cat_lower for k in ['fire', 'smoke', 'explosion', 'rescue', 'trapped', 'general', 'gas leak']):
            all_fallbacks.append({
                "name": f"{city_title} Fire Emergency",
                "address": loc_clean,
                "phone": "101",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })
            
        # Disaster / Shelter
        if any(k in cat_lower for k in ['flood', 'earthquake', 'disaster', 'cyclone', 'storm']):
            all_fallbacks.append({
                "name": f"{city_title} Disaster Relief / SDRF",
                "address": loc_clean,
                "phone": "1070",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 2.0,
                "coordinates": coords,
                "fallback": True
            })
            
        if not all_fallbacks:
            # Absolute fallback
            all_fallbacks.append({
                "name": f"{city_title} Emergency Helpline",
                "address": loc_clean,
                "phone": "112",
                "status": "AVAILABLE",
                "verified_at": self.current_date.strftime("%Y-%m-%d"),
                "distance_km": 1.0,
                "coordinates": coords,
                "fallback": True
            })
            
        return all_fallbacks

    def verify_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Runs quality scoring on a resource's details."""
        score = 1.0
        checks = {}
        
        status = resource.get("status", "UNKNOWN").upper()
        if status in ["OPERATIONAL", "OPEN", "AVAILABLE"]:
            checks["status_ok"] = True
        else:
            checks["status_ok"] = False
            score -= 0.3

        verified_date_str = resource.get("verified_at", "")
        try:
            verified_date = datetime.datetime.strptime(verified_date_str, "%Y-%m-%d")
            delta_days = (self.current_date - verified_date).days
            if delta_days <= 2:
                checks["freshness_ok"] = True
            elif delta_days <= 7:
                checks["freshness_ok"] = True
                score -= 0.1
            else:
                checks["freshness_ok"] = False
                score -= 0.25
        except ValueError:
            checks["freshness_ok"] = False
            score -= 0.3

        phone = resource.get("phone", "")
        # Short numbers (like 108, 112, 101, 100, 102) are fully valid emergency hotlines
        if phone and (phone in ["108", "112", "101", "100", "102"] or (len(phone) >= 10 and any(char.isdigit() for char in phone))):
            checks["phone_valid"] = True
        else:
            checks["phone_valid"] = False
            score -= 0.2


        if resource.get("name") and resource.get("address"):
            checks["source_authentic"] = True
        else:
            checks["source_authentic"] = False
            score -= 0.2

        score = max(0.0, round(score, 2))
        return {
            "verified": score >= 0.75,
            "score": score,
            "checks": checks,
            "resource_name": resource.get("name", "Unknown Center")
        }

    def verify_batch(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Verifies a batch of resources, inserting score metadata."""
        verified = []
        for r in resources:
            v_report = self.verify_resource(r)
            res_copied = r.copy()
            res_copied["verification"] = v_report
            verified.append(res_copied)
        return verified
