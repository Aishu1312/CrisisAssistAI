import json
import os
from typing import Dict, Any, List

class UserMemory:
    """
    Manages long-term user preferences and medical/contact context.
    Persists data locally in a JSON file to retain memory across app launches.
    """
    def __init__(self, filepath: str = "user_profile.json"):
        self.filepath = filepath
        self.profile = self.load_default_profile()
        self.load_from_disk()

    def load_default_profile(self) -> Dict[str, Any]:
        """Returns standard profile template."""
        return {
            "name": "Jane Doe",
            "preferred_language": "English",
            "communication_preference": "text",  # text, voice
            "home_location": "Mumbai, Maharashtra",
            "emergency_contact": {
                "name": "John Doe (Spouse)",
                "phone": "+91-98765-43210"
            },
            "medical_alerts": "Type 1 Diabetes, Penicillin Allergy",
            "past_emergency_summaries": []
        }

    def load_from_disk(self):
        """Loads profile from disk if it exists; otherwise creates default."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.profile = json.load(f)
            except Exception as e:
                print(f"Error loading user profile: {e}, falling back to defaults.")
                self.profile = self.load_default_profile()
        else:
            self.save_to_disk()

    def save_to_disk(self):
        """Writes current profile dictionary to disk."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=4)
        except Exception as e:
            print(f"Error saving user profile: {e}")

    def get_profile(self) -> Dict[str, Any]:
        """Returns the full user profile dictionary."""
        return self.profile

    def update_profile(self, updates: Dict[str, Any]):
        """Updates the profile with new dictionary keys and saves."""
        for key, val in updates.items():
            if key in self.profile:
                if isinstance(self.profile[key], dict) and isinstance(val, dict):
                    self.profile[key].update(val)
                else:
                    self.profile[key] = val
        self.save_to_disk()

    def add_past_request(self, query: str, priority: str, category: str, summary: str):
        """Records a past emergency request for context injection in future runs."""
        past_record = {
            "query": query,
            "priority": priority,
            "category": category,
            "summary": summary,
            "timestamp": os.path.getmtime(self.filepath) if os.path.exists(self.filepath) else 0.0
        }
        # Keep only the last 5 emergency summaries for contextual relevance
        self.profile["past_emergency_summaries"] = [past_record] + self.profile["past_emergency_summaries"][:4]
        self.save_to_disk()
