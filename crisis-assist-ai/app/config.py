import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")  # Gemini API key only

# Override placeholder key with active environment key if present
if os.getenv("GOOGLE_API_KEY") == "<paste_your_key_here>" or not os.getenv("GOOGLE_API_KEY"):
    if os.getenv("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

@dataclass
class AgentConfig:
    # Reads model from environment GEMINI_MODEL. Default gemini-2.5-flash (the 1.5 family is retired and returns 404). Use gemini-2.5-flash-lite for tighter free-tier quota.
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True

config = AgentConfig()
