import json
import os
from typing import Dict, Any, List

class UserMemory:
    """
    Manages long-term user profile memory, allergies, medical conditions,
    emergency contacts, and locations. Persists to user_profile.json.
    """
    def __init__(self, filepath: str = "user_profile.json"):
        self.filepath = filepath
        self.profile = self.load_default_profile()
        self.load_from_disk()

    def load_default_profile(self) -> Dict[str, Any]:
        return {
            "name": "Jane Doe",
            "allergies": ["Penicillin Allergy"],
            "medical_conditions": [],
            "emergency_contact": {
                "name": "John Doe (Spouse)",
                "phone": "+91-98765-43210"
            },
            "location": "Pune, Maharashtra",
            "preferred_language": "English",
            "past_emergency_summaries": []
        }

    def load_from_disk(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.profile = json.load(f)
                    
                # Ensure backwards-compatibility mapping keys
                if "home_location" in self.profile and "location" not in self.profile:
                    self.profile["location"] = self.profile["home_location"]
                if "medical_alerts" in self.profile and "allergies" not in self.profile:
                    alerts = self.profile["medical_alerts"]
                    self.profile["allergies"] = [a.strip() for a in alerts.split(",") if a.strip()]
                if "medical_conditions" not in self.profile:
                    self.profile["medical_conditions"] = []
            except Exception as e:
                print(f"Error loading user profile: {e}")
                self.profile = self.load_default_profile()
        else:
            self.save_to_disk()

    def save_to_disk(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=4)
        except Exception as e:
            print(f"Error saving user profile: {e}")

    def get_profile(self) -> Dict[str, Any]:
        return self.profile

    def update_profile(self, updates: Dict[str, Any]):
        for key, val in updates.items():
            self.profile[key] = val
            
        # Keep home_location and medical_alerts in sync for UI backward compatibility
        if "location" in self.profile:
            self.profile["home_location"] = self.profile["location"]
        if "allergies" in self.profile:
            if isinstance(self.profile["allergies"], list):
                self.profile["medical_alerts"] = ", ".join(self.profile["allergies"])
            else:
                self.profile["medical_alerts"] = str(self.profile["allergies"])
                # Also convert allergies back to list if it was a string
                self.profile["allergies"] = [a.strip() for a in str(self.profile["allergies"]).split(",") if a.strip()]
        self.save_to_disk()

    def add_past_request(self, query: str, priority: str, category: str, summary: str):
        past_record = {
            "query": query,
            "priority": priority,
            "category": category,
            "summary": summary,
            "timestamp": os.path.getmtime(self.filepath) if os.path.exists(self.filepath) else 0.0
        }
        if "past_emergency_summaries" not in self.profile:
            self.profile["past_emergency_summaries"] = []
        self.profile["past_emergency_summaries"] = [past_record] + self.profile["past_emergency_summaries"][:4]
        self.save_to_disk()
