import datetime
from typing import List, Dict, Any

class SessionMemory:
    """
    Manages short-term, in-memory storage for the current active emergency response session.
    Tracks conversation logs, tool execution steps, and agent timeline traces.
    """
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.agent_steps: List[Dict[str, Any]] = []
        self.current_priority: str = "UNKNOWN"
        self.detected_category: str = "UNKNOWN"
        self.last_decision_explanation: str = ""
        self.verified_resources: List[Dict[str, Any]] = []
        self.session_start_time = datetime.datetime.now()

    def add_user_message(self, message: str, detected_lang: str = "en"):
        """Adds a message sent by the user to the transcript."""
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "language": detected_lang,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def add_agent_message(self, role: str, content: str, lang: str = "en", audio_path: str = None):
        """Adds a message sent by the system/agent to the transcript."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "language": lang,
            "audio_path": audio_path,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def add_step(self, agent_name: str, action: str, status: str, details: Any = None):
        """
        Logs a micro-step in the multi-agent activity timeline.
        Used to feed the agent execution dashboard.
        """
        self.agent_steps.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "status": status,
            "details": details
        })

    def set_emergency_meta(self, priority: str, category: str, explanation: str):
        """Sets metadata for the current query lifecycle."""
        self.current_priority = priority
        self.detected_category = category
        self.last_decision_explanation = explanation

    def set_verified_resources(self, resources: List[Dict[str, Any]]):
        """Stores resources found and verified for the current query."""
        self.verified_resources = resources

    def clear(self):
        """Reset short-term session memory."""
        self.conversation_history.clear()
        self.agent_steps.clear()
        self.current_priority = "UNKNOWN"
        self.detected_category = "UNKNOWN"
        self.last_decision_explanation = ""
        self.verified_resources.clear()
        self.session_start_time = datetime.datetime.now()

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Returns the list of agent steps formatted for UI rendering."""
        return self.agent_steps

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns the full conversation log."""
        return self.conversation_history
