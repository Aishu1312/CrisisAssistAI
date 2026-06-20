import datetime
import uuid
from typing import Dict, Any, Optional

class AgentMessage:
    """
    Standardized A2A communication envelope.
    Includes trace IDs to track collaborative agents steps.
    """
    def __init__(
        self,
        sender: str,
        receiver: str,
        message_type: str,
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
