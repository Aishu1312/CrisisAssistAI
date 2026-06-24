import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "False")  # Gemini API key only

# Sync API keys to support both google-genai and older SDK expectations
gemini_key = os.getenv("GEMINI_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
if google_key == "<paste_your_key_here>":
    google_key = None

if gemini_key and not google_key:
    os.environ["GOOGLE_API_KEY"] = gemini_key
elif google_key and not gemini_key:
    os.environ["GEMINI_API_KEY"] = google_key

@dataclass
class AgentConfig:
    # Reads model from environment GEMINI_MODEL. Default gemini-2.5-flash (the 1.5 family is retired and returns 404). Use gemini-2.5-flash-lite for tighter free-tier quota.
    model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    mcp_server_port: int = 8090
    max_iterations: int = 3
    pii_redaction_enabled: bool = True
    injection_detection_enabled: bool = True

config = AgentConfig()
