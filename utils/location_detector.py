import requests
import json
import re
from typing import Dict, Any, Tuple
import streamlit as st
from utils.gemini_helper import safe_generate_content

class LocationDetector:
    """
    Handles dynamic location detection using:
    1. Browser/geolocation
    2. IP based location via st.context
    3. Manual location input fallback
    """
    def __init__(self, gemini_client=None):
        self.client = gemini_client

    def detect_from_ip(self) -> Dict[str, Any]:
        """
        Attempts to detect location via public IP using ip-api.com.
        Uses st.context for client IP mapping.
        """
        try:
            ip_address = ""
            if hasattr(st, "context"):
                if hasattr(st.context, "ip_address") and st.context.ip_address:
                    ip_address = st.context.ip_address
                elif hasattr(st.context, "headers"):
                    x_forward = st.context.headers.get("x-forwarded-for")
                    if x_forward:
                        ip_address = x_forward.split(",")[0].strip()

            url = f"http://ip-api.com/json/{ip_address}" if ip_address else "http://ip-api.com/json/"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "city": data.get("city", "Mumbai"),
                        "state": data.get("regionName", "Maharashtra"),
                        "country": data.get("country", "India"),
                        "coords": (float(data.get("lat", 19.0760)), float(data.get("lon", 72.8777)))
                    }
        except Exception as e:
            print(f"IP-based location detection failed: {e}")
        
        # Safe default fallback
        return {
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "coords": (19.0760, 72.8777)
        }

    def reverse_geocode(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Reverse geocodes coordinates to city, state, country using Gemini model.
        """
        if self.client:
            try:
                prompt = (
                    f"Reverse geocode these coordinates: latitude={lat}, longitude={lon}.\n"
                    "Return ONLY a valid JSON object with keys: 'city', 'state', 'country'. "
                    "Do not include markdown tags, code blocks, or explanations."
                )
                response = safe_generate_content(
                    self.client,
                    model="gemini-flash-latest",
                    contents=prompt
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                
                data = json.loads(text)
                return {
                    "city": data.get("city", "Mumbai"),
                    "state": data.get("state", "Maharashtra"),
                    "country": data.get("country", "India"),
                    "coords": (lat, lon)
                }
            except Exception as e:
                print(f"Gemini reverse geocode failed: {e}. Falling back to default.")
        
        return {
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "coords": (lat, lon)
        }

    def parse_manual_location(self, location_str: str) -> Dict[str, Any]:
        """
        Parses a manually entered location string (e.g. 'Pune, Maharashtra') 
        and extracts coordinates and parts using Gemini.
        """
        if not location_str or location_str.strip() == "":
            return self.detect_from_ip()

        # Simple split fallback
        parts = [p.strip() for p in location_str.split(",")]
        city = parts[0]
        state = parts[1] if len(parts) > 1 else ""
        country = parts[2] if len(parts) > 2 else "India"

        # Simulating coordinates or geocoding via Gemini
        coords = (19.0760, 72.8777)
        if self.client:
            try:
                prompt = (
                    f"Geocode the location: '{location_str}'.\n"
                    "Return ONLY a valid JSON object with keys: 'city', 'state', 'country', 'latitude', 'longitude'. "
                    "Do not include markdown tags, code blocks, or explanations."
                )
                response = safe_generate_content(
                    self.client,
                    model="gemini-flash-latest",
                    contents=prompt
                )
                text = response.text.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n", "", text)
                    text = re.sub(r"\n```$", "", text)
                
                data = json.loads(text)
                return {
                    "city": city,
                    "state": state,
                    "country": country,
                    "coords": (float(data.get("latitude", 19.0760)), float(data.get("longitude", 72.8777)))
                }
            except Exception as e:
                print(f"Gemini geocoding of manual location failed: {e}")

        return {
            "city": city,
            "state": state,
            "country": country,
            "coords": coords
        }
