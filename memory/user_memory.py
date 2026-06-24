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
            "name": "Arjun Mehta",
            "location": "Nagpur, Maharashtra",
            "home_location": "Nagpur, Maharashtra",
            "medical_alerts": "Milk, Dust",
            "allergies": ["Milk", "Dust"],
            "medical_conditions": ["Anxiety", "Depression", "PCOD"],
            "contact_name": "Deepa Mehta (Wife)",
            "contact_phone": "+91-98989-12345",
            "emergency_contact": {
                "name": "Deepa Mehta (Wife)",
                "phone": "+91-98989-12345"
            },
            "preferred_language": "English",
            "past_emergency_summaries": [
                {
                    "category": "Fire Hazard",
                    "priority": "CRITICAL",
                    "summary": "Emergency resolved in Mumbai.",
                    "query": "There is a fire in my apartment building"
                },
                {
                    "category": "General Support",
                    "priority": "LOW",
                    "summary": "Emergency type General Support classified as LOW. Location: Pune.",
                    "query": "Need general assistance in Pune"
                },
                {
                    "category": "Medical Emergency",
                    "priority": "CRITICAL",
                    "summary": "Emergency type Medical classified as CRITICAL. Location: Pune.",
                    "query": "Urgent medical assistance required in Pune"
                }
            ]
        }

    def load_from_disk(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.profile = json.load(f)

                # Ensure backwards-compatibility mapping keys
                if "location" in self.profile:
                    self.profile["home_location"] = self.profile["location"]
                elif "home_location" in self.profile:
                    self.profile["location"] = self.profile["home_location"]
                    
                if "medical_alerts" in self.profile:
                    alerts = self.profile["medical_alerts"]
                    if isinstance(alerts, list):
                        self.profile["medical_alerts"] = ", ".join(alerts)
                        self.profile["allergies"] = alerts
                    else:
                        self.profile["medical_alerts"] = str(alerts)
                        self.profile["allergies"] = [a.strip() for a in str(alerts).split(",") if a.strip()]
                elif "allergies" in self.profile:
                    alerts = self.profile["allergies"]
                    if isinstance(alerts, list):
                        self.profile["medical_alerts"] = ", ".join(alerts)
                        self.profile["allergies"] = alerts
                    else:
                        self.profile["medical_alerts"] = str(alerts)
                        self.profile["allergies"] = [a.strip() for a in str(alerts).split(",") if a.strip()]
                
                if "medical_conditions" not in self.profile:
                    self.profile["medical_conditions"] = []
                    
                if "past_emergency_summaries" not in self.profile or not self.profile["past_emergency_summaries"]:
                    # If empty, load the default mock past requests
                    self.profile["past_emergency_summaries"] = [
                        {
                            "category": "Fire Hazard",
                            "priority": "CRITICAL",
                            "summary": "Emergency resolved in Mumbai.",
                            "query": "There is a fire in my apartment building"
                        },
                        {
                            "category": "General Support",
                            "priority": "LOW",
                            "summary": "Emergency type General Support classified as LOW. Location: Pune.",
                            "query": "Need general assistance in Pune"
                        },
                        {
                            "category": "Medical Emergency",
                            "priority": "CRITICAL",
                            "summary": "Emergency type Medical classified as CRITICAL. Location: Pune.",
                            "query": "Urgent medical assistance required in Pune"
                        }
                    ]
                    
                contact = self.profile.get("emergency_contact", {})
                if not isinstance(contact, dict):
                    contact = {}
                if "contact_name" in self.profile:
                    contact["name"] = self.profile["contact_name"]
                elif "name" in contact:
                    self.profile["contact_name"] = contact["name"]
                if "contact_phone" in self.profile:
                    contact["phone"] = self.profile["contact_phone"]
                elif "phone" in contact:
                    self.profile["contact_phone"] = contact["phone"]
                self.profile["emergency_contact"] = contact
                
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
            
        # Ensure flat keys requested are stored
        if "location" in self.profile:
            self.profile["home_location"] = self.profile["location"]
            
        # Keep medical_alerts and allergies list in sync based on what was updated
        if "allergies" in updates:
            allergies = updates["allergies"]
            if isinstance(allergies, list):
                self.profile["medical_alerts"] = ", ".join(allergies)
                self.profile["allergies"] = allergies
            else:
                self.profile["medical_alerts"] = str(allergies)
                self.profile["allergies"] = [a.strip() for a in str(allergies).split(",") if a.strip()]
        elif "medical_alerts" in updates:
            alerts = updates["medical_alerts"]
            if isinstance(alerts, list):
                self.profile["medical_alerts"] = ", ".join(alerts)
                self.profile["allergies"] = alerts
            else:
                self.profile["medical_alerts"] = str(alerts)
                self.profile["allergies"] = [a.strip() for a in str(alerts).split(",") if a.strip()]
        else:
            # Fallback sync if neither is in updates
            if "allergies" in self.profile:
                allergies = self.profile["allergies"]
                if isinstance(allergies, list):
                    self.profile["medical_alerts"] = ", ".join(allergies)
                else:
                    self.profile["medical_alerts"] = str(allergies)
                    self.profile["allergies"] = [a.strip() for a in str(allergies).split(",") if a.strip()]

        # Keep emergency_contact dict and contact_name/contact_phone flat keys in sync
        contact = self.profile.get("emergency_contact", {})
        if not isinstance(contact, dict):
            contact = {}
            
        if "emergency_contact" in updates:
            contact = updates["emergency_contact"]
            self.profile["contact_name"] = contact.get("name", "")
            self.profile["contact_phone"] = contact.get("phone", "")
        else:
            if "contact_name" in updates:
                contact["name"] = updates["contact_name"]
            if "contact_phone" in updates:
                contact["phone"] = updates["contact_phone"]
                
        self.profile["emergency_contact"] = contact
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
