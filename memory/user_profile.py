import json
import os
from typing import Dict, Any, List

class UserProfile:
    """
    Manages long-term user profile data, preferences, emergency contacts, 
    and medical alerts. Persists to user_profile.json.
    """
    def __init__(self, filepath: str = "user_profile.json"):
        self.filepath = filepath
        self.profile = self.load_default_profile()
        self.load_from_disk()

    def load_default_profile(self) -> Dict[str, Any]:
        return {
            "name": "Jane Doe",
            "preferred_language": "English",
            "communication_preference": "text",
            "home_location": "Mumbai, Maharashtra",
            "medical_alerts": "Type 1 Diabetes, Penicillin Allergy",
            "emergency_contact": {
                "name": "John Doe (Spouse)",
                "phone": "+91-98765-43210"
            },
            "past_emergency_summaries": []
        }

    def load_from_disk(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.profile = json.load(f)
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
            if key in self.profile:
                if isinstance(self.profile[key], dict) and isinstance(val, dict):
                    self.profile[key].update(val)
                else:
                    self.profile[key] = val
            else:
                # Support arbitrary field updates
                self.profile[key] = val
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
