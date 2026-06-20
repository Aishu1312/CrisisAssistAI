import datetime
import uuid
from typing import Dict, Any, Optional

class AgentMessage:
    """
    Represents a standardized message envelope for Agent-to-Agent (A2A) communication.
    Ensures structured and trace-compatible information exchange.
    """
    def __init__(
        self,
        sender: str,
        receiver: str,
        message_type: str,  # "REQUEST", "RESPONSE", "PLAN", "EVAL_FEEDBACK", "EVAL_RESULT"
        payload: Dict[str, Any],
        trace_id: Optional[str] = None
    ):
        self.message_id = str(uuid.uuid4())
        self.trace_id = trace_id or str(uuid.uuid4())
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type.upper()
        self.payload = payload
        self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the A2A message into a standard dictionary."""
        return {
            "message_id": self.message_id,
            "trace_id": self.trace_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Constructs an AgentMessage from a dictionary."""
        msg = cls(
            sender=data["sender"],
            receiver=data["receiver"],
            message_type=data["message_type"],
            payload=data["payload"],
            trace_id=data.get("trace_id")
        )
        msg.message_id = data["message_id"]
        msg.timestamp = data["timestamp"]
        return msg
