import datetime
from typing import List, Dict, Any

class SessionMemory:
    """
    Manages short-term, in-memory storage for the active emergency response session.
    Tracks conversation transcripts, micro-steps, and real-time agent statuses.
    """
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.agent_steps: List[Dict[str, Any]] = []
        self.current_priority: str = "UNKNOWN"
        self.detected_category: str = "UNKNOWN"
        self.last_decision_explanation: str = ""
        self.verified_resources: List[Dict[str, Any]] = []
        self.past_emergencies: List[Dict[str, Any]] = []
        self.session_start_time = datetime.datetime.now()
        # Current active agent: "none", "planning", "executing", "validating"
        self.active_agent: str = "none"

    def add_user_message(self, message: str, detected_lang: str = "en"):
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "language": detected_lang,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def add_agent_message(self, role: str, content: str, lang: str = "en", audio_path: str = None):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "language": lang,
            "audio_path": audio_path,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def add_step(self, agent_name: str, action: str, status: str, details: Any = None):
        self.agent_steps.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "status": status,
            "details": details
        })
        
        # Dynamically set the active agent status for UI workflow visualization
        name_lower = agent_name.lower()
        status_lower = status.lower()
        if "planner" in name_lower:
            self.active_agent = "planning" if status_lower == "started" else "none"
        elif "worker" in name_lower:
            self.active_agent = "executing" if status_lower == "started" else "none"
        elif "evaluator" in name_lower:
            self.active_agent = "validating" if status_lower == "started" else "none"

    def set_emergency_meta(self, priority: str, category: str, explanation: str):
        self.current_priority = priority
        self.detected_category = category
        self.last_decision_explanation = explanation

    def add_past_emergency(self, category: str, priority: str, city: str):
        self.past_emergencies.append({
            "category": category,
            "priority": priority,
            "city": city,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def set_verified_resources(self, resources: List[Dict[str, Any]]):
        self.verified_resources = resources

    def clear(self):
        self.conversation_history.clear()
        self.agent_steps.clear()
        self.current_priority = "UNKNOWN"
        self.detected_category = "UNKNOWN"
        self.last_decision_explanation = ""
        self.verified_resources.clear()
        self.active_agent = "none"
        self.session_start_time = datetime.datetime.now()

    def get_timeline(self) -> List[Dict[str, Any]]:
        return self.agent_steps

    def get_history(self) -> List[Dict[str, Any]]:
        return self.conversation_history

    def get_past_emergencies(self) -> List[Dict[str, Any]]:
        return self.past_emergencies
